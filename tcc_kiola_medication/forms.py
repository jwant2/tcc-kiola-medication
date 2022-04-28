import csv
import io
from decimal import Decimal

from diplomat.models import ISOCountry, ISOLanguage
from django import forms
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.forms import ModelForm
from django.forms.utils import ErrorList
from django.utils import timezone
from django.utils.timezone import localtime, now
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext_noop

from kiola.cares import widgets as cares_widgets
from kiola.kiola_med import const as med_const
from kiola.kiola_med import models as med_models
from kiola.kiola_med import utils as med_utils
from kiola.kiola_med.forms import SimplePrescriptionForm
from kiola.kiola_organizer import utils as organizer_utils
from kiola.kiola_pharmacy import models as pharmacy_models
from kiola.kiola_senses import forms as senses_forms
from kiola.kiola_senses import models as senses_models
from kiola.themes import widgets as themes_widgets
from kiola.utils import forms as kiola_forms
from kiola.utils.signals import signal_registry

from . import const, models


class CompoundImportHistoryForm(ModelForm):
    source_file = forms.FileField(label=_("Source file"), required=True)
    data_source_description = forms.CharField(
        label=_("Data source description"), required=False
    )
    data_source_version = forms.CharField(label=_("Version"), required=True)

    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        initial=None,
        error_class=ErrorList,
        label_suffix=None,
        empty_permitted=False,
        instance=None,
        use_required_attribute=None,
        renderer=None,
    ):
        super(CompoundImportHistoryForm, self).__init__(
            data,
            files,
            auto_id,
            prefix,
            initial,
            error_class,
            label_suffix,
            empty_permitted,
            instance,
        )

    class Meta:
        model = pharmacy_models.ImportHistory
        # fields = ("status", "details", "source_file")
        fields = ("source_file",)

    def clean(self):
        cleaned_data = super().clean()
        file_data = cleaned_data["source_file"]
        if not file_data.name.endswith(".csv"):
            msg = f"Source file must be a csv file"
            self.add_error("source_file", msg)
        exist = (
            med_models.CompoundSource.objects.filter(
                name=const.COMPOUND_SOURCE_NAME__TCC,
                version=cleaned_data["data_source_version"],
            ).count()
            > 0
        )

        if exist:
            msg = f"Given data source version already exist!"
            self.add_error("data_source_version", msg)

    def save(self, commit=True):

        error_logs = []
        descrition = self.cleaned_data["data_source_description"]
        version = self.cleaned_data["data_source_version"]
        file_data = self.cleaned_data["source_file"]
        # prepare csv file
        data_set = file_data.read().decode("UTF-8")
        io_string = io.StringIO(data_set)
        next(io_string)

        # create a new ImportHistory
        with transaction.atomic():
            pharmacy_models.ImportHistory.objects.filter(status="S").update(status="F")
        with transaction.atomic():
            self.instance = pharmacy_models.ImportHistory.objects.create(
                status="S", source_file=file_data.name
            )

        # create new compound source
        source, created = med_models.CompoundSource.objects.get_or_create(
            name=const.COMPOUND_SOURCE_NAME__TCC,
            version=version,
            language=ISOLanguage.objects.get(alpha2="en"),
            country=ISOCountry.objects.get(alpha2="AU"),
            group="TCC",
            default=True,
        )

        formulations = {}
        # FIXME: unable to handle any other PBS data format
        # loop csv file data row by row
        for column in csv.reader(
            io_string, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL
        ):
            try:
                # process and create active components data

                ac, created = med_models.ActiveComponent.objects.get_or_create(
                    name=column[0]
                )
                if created:
                    ac.name_ref = column[4]
                    ac.save()

                # process SCH/PRN
                prn_value = column[32]
                if prn_value == "Yes":
                    med_type = const.MEDICATION_TYPE_VALUE__REGULAR
                else:
                    med_type = const.MEDICATION_TYPE_VALUE__PRN

                dosageform = column[26]
                dosageform_ref = dosageform[:3].upper()
                if dosageform == "":
                    dosageform = "N/A"
                    dosageform_ref = "N/A"
                else:
                    formulations[dosageform] = dosageform_ref
                    # unit, created = med_models.TakingUnit.objects.get_or_create(name=dosageform)
                    # if created:
                    #     unit.descrition=dosageform_ref
                    #     unit.save
                # create or update medication product data
                pharmacy_models.Product.objects.update_or_create(
                    unique_id=column[4],
                    defaults={
                        "title": column[1],
                        "unique_id": column[4],
                        "meta_data": '{"active_components": {"1":"'
                        + column[0]
                        + '"}, "SCH/PRN": "'
                        + prn_value
                        + '", "source": {"name": "'
                        + const.COMPOUND_SOURCE_NAME__TCC
                        + '", "version": "'
                        + version
                        + '"}, "dosage_form": {"'
                        + dosageform_ref
                        + '": "'
                        + dosageform
                        + '"}}',
                    },
                )
                # create or update compound data
                compound, created = med_models.Compound.objects.update_or_create(
                    uid=column[4],
                    name=column[1],
                    defaults={
                        "source": source,
                        "name": column[1],
                        "dosage_form": column[26],
                    },
                )
                active_components = compound.active_components.all()
                compound.active_components.add(ac)
                compound.save()

                # store PRN data
                prn, created = models.CompoundExtraInformation.objects.get_or_create(
                    compound=compound,
                    name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE,
                )
                if created:
                    prn.value = med_type
                    prn.save()

            except Exception as error:
                # store error data row and error message in ImportHistory.details
                error_log = {"error_msg": str(error), "error_data": column}
                error_logs.append(error_log)

        for key in formulations.keys():
            unit, created = med_models.TakingUnit.objects.get_or_create(name=key)
            if created:
                unit.descrition = formulations[key]
                unit.save

        # finalise ImportHistory record
        with transaction.atomic():
            self.instance.status = "C"
            self.instance.details = error_logs
            self.instance.ended = timezone.now()
            self.instance.save()

        return super(CompoundImportHistoryForm, self).save(commit=commit)


class TCCPrescriptionDataLoader(kiola_forms.InitialDataLoader):
    def load(self, request, fid=None, **kwargs):
        data = {}
        if fid is not None:
            subject = senses_models.Subject.objects.get(uuid=request.subject_uid)
            prescription = models.TCCPrescription.objects.get(pk=fid, subject=subject)
            data["status"] = prescription.status.id
            data["compound_id"] = prescription.compound.uid
            data["compound_source"] = str(prescription.compound.source.pk)
            start = prescription.prescriptionevent_set.filter(
                etype=med_models.PrescriptionEventType.objects.get(
                    name=med_const.EVENT_TYPE__PRESCRIBED
                )
            )[0]
            data["ev__prescription_startdate"] = localtime(start.timepoint).date
            end = prescription.prescriptionevent_set.filter(
                etype=med_models.PrescriptionEventType.objects.get(
                    name=med_const.EVENT_TYPE__END
                )
            )
            if len(end) > 0:
                data["ev__prescription_enddate"] = localtime(end[0].timepoint).date
            data["taking_hint"] = prescription.taking_hint
            data["taking_reason"] = prescription.taking_reason
            schema = prescription.prescriptionschema_set.all()[0]
            takings = schema.taking_schema.takings.all()
            data["unit"] = prescription.unit.name
            data["dosage"] = prescription.dosage
            data["strength"] = prescription.strength
            data["med_type"] = prescription.medication_type.name
        else:
            # FIXME:cgo: this should be configurable to support different data sources
            try:
                data["compound_source"] = (
                    med_models.CompoundSource.objects.filter(default=True)
                    .order_by("-pk")[0]
                    .pk
                )
            except IndexError as details:
                raise AttributeError(
                    "No default compound source found - has the med database been properly set up ?"
                )
            data["taking_unit"] = med_models.TakingUnit.objects.get(
                name=med_const.TAKING_UNIT__UNIT
            ).pk

        return data


class TCCPrescriptionForm(senses_forms.KiolaSubjectForm):
    title = _("Prescription")
    loader = TCCPrescriptionDataLoader()

    class Media:
        js = ("autocomplete.js", "text_widget.js")
        css = {"all": ["fa-time.css", "css/kiola-fonts.css"]}

    def __init__(self, *args, **kwargs):
        super(TCCPrescriptionForm, self).__init__(*args, **kwargs)

        date_options = signal_registry.send_to_category(
            "request_datetime_field_options", self, {"fieldtype": "date"}
        )[0][1][0][1]
        self.fields["ev__prescription_startdate"] = forms.DateField(
            label=_("Date of prescription"),
            required=True,
            initial=now().date(),
            **date_options,
        )
        self.fields["ev__prescription_startdate"].label += " *"
        self.fields["ev__prescription_startdate"].widget.attrs.update(
            {"autocomplete": "off", "placeholder": "DD/MM/YYYY"}
        )
        self.fields["status"] = forms.IntegerField(
            widget=forms.HiddenInput(), required=False
        )

        self.fields["compound_id"] = forms.CharField(
            widget=forms.HiddenInput(), required=True
        )
        self.fields["compound_source"] = forms.CharField(
            widget=forms.HiddenInput(), required=True
        )
        self.fields["dosage"] = forms.CharField(
            label=_("Dosage *"), required=True, help_text="i.e. 4 pills", max_length=400
        )
        self.fields["strength"] = forms.CharField(
            label=_("Strength *"),
            required=True,
            help_text="i.e. 200 mg",
            max_length=100,
        )
        self.fields["unit"] = forms.CharField(
            label=_("Formulation *"),
            required=True,
            help_text="i.e. Tablet/Pill/Solution/etc..",
            max_length=30,
        )
        unit_list = med_models.TakingUnit.objects.all().values_list("name", flat=True)
        self.fields["unit"].widget = ListTextWidget(
            data_list=unit_list, name="formulation_list"
        )
        self.fields["taking_reason"] = forms.CharField(
            label=_("Reason of prescription"), required=False, max_length=100
        )
        self.fields["taking_hint"] = forms.CharField(
            label=_("Hint for taking"),
            required=False,
            widget=forms.Textarea(),
            max_length=400,
        )

        choices = [
            (const.MEDICATION_TYPE_VALUE__PRN, const.MEDICATION_TYPE_VALUE__PRN),
            (
                const.MEDICATION_TYPE_VALUE__REGULAR,
                const.MEDICATION_TYPE_VALUE__REGULAR,
            ),
        ]
        self.fields["med_type"] = forms.ChoiceField(
            choices=choices,
            widget=themes_widgets.RadioSelect(
                renderer=cares_widgets.HorizontalRadioRenderer,
                attrs={"wrapper-class": "radio-option-space2x"},
            ),
            required=True,
            label="Medication type(SCH/PRN) *",
        )

        self.fields["taking"] = forms.CharField(
            widget=forms.HiddenInput(), required=False
        )

        date_options = signal_registry.send_to_category(
            "request_datetime_field_options", self, {"fieldtype": "date"}
        )[0][1][0][1]
        self.fields["ev__prescription_enddate"] = forms.DateField(
            label=_("Stop taking"), required=False, **date_options
        )
        self.fields["ev__prescription_enddate"].widget.attrs.update(
            {"autocomplete": "off", "placeholder": "DD/MM/YYYY"}
        )
        self.fields["sis_search"] = forms.CharField(
            label=_("SIS search"),
            widget=forms.TextInput(
                attrs={
                    "placeholder": _("Type here to search"),
                }
            ),
            required=False,
        )

        if getattr(self, "_kiola_option__disabled", False):
            self.disable_all()
        else:
            # the buttons
            if self.fid is None:
                self.buttons.append(
                    kiola_forms.SubmitButton(ugettext_noop("Save"), self.savenew)
                )
            else:
                self.buttons.append(
                    kiola_forms.SubmitButton(
                        ugettext_noop("Save"), self.update_or_create
                    )
                )

        self.buttons.insert(
            0,
            kiola_forms.BackToListButton(
                ugettext_noop("Back"),
                None,
                {
                    "listname": "med:prescription_index",
                    "url_reverse_params": {"sid": self.sid},
                },
            ),
        )

    def clean(self):

        cd = super(TCCPrescriptionForm, self).clean()
        cd["unit"] = cd["unit"].strip()
        if len(cd.get("compound_id", "")) == 0:
            raise forms.ValidationError(_("Please select a compound"))
        return cd

    def savenew(self, request, proxy=False):

        cd = self.cleaned_data
        subject = senses_models.Subject.objects.get(uuid=request.subject_uid)
        adapter = med_models.Compound.objects.get_adapter(cd["compound_source"])
        compound, created = adapter.get_or_create(cd["compound_id"])

        medication_type = models.MedicationType.objects.get(name=cd["med_type"])
        unit, created = med_models.TakingUnit.objects.get_or_create(name=cd["unit"])
        prescription, replaced = models.TCCPrescription.objects.prescribe(
            subject=subject,
            prescriber=request.user,
            compound=compound,
            reason=cd["taking_reason"],
            hint=cd["taking_hint"],
            start=cd["ev__prescription_startdate"],
            dosage=cd["dosage"],
            strength=cd["strength"],
            unit=unit,
            med_type=medication_type,
            end=cd.get("ev__prescription_enddate", None),
        )

        if not self.fid:
            self.fid = prescription.pk

        if replaced:
            messages.info(request, _("Replaced existing prescription of same compound"))

        if not proxy:
            messages.success(
                request,
                _("Prescription added: {compound}").format(compound=compound.name),
            )

    def update_or_create(self, request):
        cd = self.cleaned_data

        prescription = models.TCCPrescription.objects.get(pk=self.fid)
        compound = prescription.compound

        prescription.taking_hint = cd["taking_hint"]
        prescription.taking_reason = cd["taking_reason"]
        medication_type = models.MedicationType.objects.get(name=cd["med_type"])
        unit, created = med_models.TakingUnit.objects.get_or_create(name=cd["unit"])
        start = prescription.prescriptionevent_set.filter(
            etype=med_models.PrescriptionEventType.objects.get(
                name=med_const.EVENT_TYPE__PRESCRIBED
            )
        )[0]
        start.timepoint = cd["ev__prescription_startdate"]
        start.save()
        if cd.get("ev__prescription_enddate", None):
            end = prescription.prescriptionevent_set.filter(
                etype=med_models.PrescriptionEventType.objects.get(
                    name=med_const.EVENT_TYPE__END
                )
            )
            if len(end) > 0:
                end[0].timepoint = cd["ev__prescription_enddate"]
                end[0].save()
            else:
                med_models.PrescriptionEvent.objects.create(
                    prescription=prescription,
                    timepoint=cd["ev__prescription_enddate"],
                    etype=med_models.PrescriptionEventType.objects.get(
                        name=med_const.EVENT_TYPE__END
                    ),
                )

        prescription.medication_type = medication_type
        prescription.dosage = cd["dosage"]
        prescription.strength = cd["strength"]
        prescription.unit = unit
        prescription.save()
        messages.success(
            request, _("Prescription saved: {compound}").format(compound=compound.name)
        )

    def remove(self, request):
        pass


class ScheduleTakingForm(ModelForm):
    template_name = "forms/schedule_taking_form.html"
    id = forms.CharField(widget=forms.HiddenInput(), required=False)
    active = forms.BooleanField(
        widget=forms.HiddenInput(), initial=True, required=False
    )

    class Meta:
        js = ("autocomplete.js", "text_widget.js")
        css = {"all": ["fa-time.css", "css/kiola-fonts.css"]}
        model = models.ScheduledTaking
        fields = (
            "frequency",
            "timepoint",
            "taking_time",
            "start_date",
            "end_date",
            "strength",
            "dosage",
            "unit",
            "hint",
            "reminder",
        )

    def __init__(self, *args, **kwargs):
        super(ScheduleTakingForm, self).__init__(*args, **kwargs)
        self.fields["timepoint"].queryset = med_models.TakingTimepoint.objects.filter(
            name__in=["morning", "noon", "afternoon", "night", "custom"]
        ).order_by("pk")
        self.fields["timepoint"].required = False
        time_options = signal_registry.send_to_category(
            "request_datetime_field_options", self, {"fieldtype": "time"}
        )[0][1][0][1]
        self.fields["taking_time"] = forms.TimeField(
            label=_("Custom time of taking medication"),
            required=False,
            **organizer_utils.time_options(),
        )
        self.fields["taking_time"].widget.attrs.update({"autocomplete": "off"})
        date_options = signal_registry.send_to_category(
            "request_datetime_field_options", self, {"fieldtype": "date"}
        )[0][1][0][1]
        self.fields["start_date"] = forms.DateField(
            label=_("Start date of taking medication *"),
            required=True,
            initial=now().date(),
            **date_options,
        )
        self.fields["start_date"].widget.attrs.update(
            {"autocomplete": "off", "placeholder": "DD/MM/YYYY"}
        )
        self.fields["end_date"] = forms.DateField(
            label=_("End date of taking medication"), required=False, **date_options
        )
        self.fields["end_date"].widget.attrs.update(
            {"autocomplete": "off", "placeholder": "DD/MM/YYYY"}
        )

        self.fields["hint"].required = False
        self.fields["strength"].label += " *"
        self.fields["dosage"].label += " *"
        self.fields["unit"] = forms.CharField(
            label=_("Formulation *"), required=True, max_length=30
        )
        unit_list = med_models.TakingUnit.objects.all().values_list("name", flat=True)
        self.fields["unit"].widget = ListTextWidget(
            data_list=unit_list, name="formulation_list"
        )
        self.fields["frequency"].label += " *"
        self.fields["timepoint"].label += " *"

    def clean(self):
        if type(self.cleaned_data["unit"]) is str:
            unit_value = self.cleaned_data["unit"]
            unit, _ = med_models.TakingUnit.objects.get_or_create(
                name=unit_value.strip()
            )
            self.cleaned_data["unit"] = unit
        return super().clean()


class ListTextWidget(forms.TextInput):
    def __init__(self, data_list, name, *args, **kwargs):
        super(ListTextWidget, self).__init__(*args, **kwargs)
        self._name = name
        self._list = data_list
        self.attrs.update({"list": "list__%s" % self._name})

    def render(self, name, value, attrs=None, renderer=None):
        text_html = super(ListTextWidget, self).render(name, value, attrs=attrs)
        data_list = '<datalist id="list__%s">' % self._name
        for item in self._list:
            data_list += '<option value="%s">' % item
        data_list += "</datalist>"

        return text_html + data_list
