

from django.utils.translation import get_language, ugettext_lazy as _
from django import forms
from django.forms import ModelForm
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.forms.utils import ErrorList
from diplomat.models import ISOLanguage, ISOCountry
from django.db import transaction

import csv, io
from django.utils import timezone
from kiola.kiola_med import models as med_models
from kiola.kiola_pharmacy import models as pharmacy_models
from . import models, const

class CompoundImportHistoryForm(ModelForm):
    source_file = forms.FileField(label=_("Source file"), required=True)
    data_source_name = forms.CharField(label=_("Data source name"), required=True)
    data_source_description = forms.CharField(label=_("Description"), required=False)
    data_source_version = forms.CharField(label=_("Version"), required=True)

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=None,
                 empty_permitted=False, instance=None, 
                 use_required_attribute=None, renderer=None):
        super(CompoundImportHistoryForm, self).__init__(data, files, auto_id, prefix,
                                                      initial, error_class, label_suffix,
                                                      empty_permitted, instance)


    class Meta:
        model = pharmacy_models.ImportHistory
        # fields = ("status", "details", "source_file")        
        fields = ("source_file",)

    def clean(self):
        cleaned_data = super().clean()
        file_data = cleaned_data['source_file']
        if not file_data.name.endswith('.csv'):
            msg = (f'Source file must be a csv file')
            self.add_error('source_file' , msg)
        exist = med_models.CompoundSource.objects.filter(name=cleaned_data['data_source_name'], version=cleaned_data['data_source_version']).count() > 0

        if exist:
            msg = (f'Given source name and version already exist!')
            self.add_error('data_source_name' , msg)
            self.add_error('data_source_version' , msg)


    def save(self, commit=True):

        error_logs = []
        name = self.cleaned_data['data_source_name']
        descrition = self.cleaned_data['data_source_description']
        version = self.cleaned_data['data_source_version']
        file_data = self.cleaned_data['source_file']
        # prepare csv file
        data_set = file_data.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string)

        # create a new ImportHistory
        with transaction.atomic():
            pharmacy_models.ImportHistory.objects.filter(status="S").update(status="F")
        with transaction.atomic():
            self.instance = pharmacy_models.ImportHistory.objects.create(status="S", source_file=file_data.name)

        # create new compound source
        source, created = med_models.CompoundSource.objects.get_or_create(name=name,
                                  version=version,
                                  language=ISOLanguage.objects.get(alpha2='en'),
                                  country=ISOCountry.objects.get(alpha2="AU"),
                                  group="TCC",
                                  default=True,
                                )
        # FIXME: unable to handle any other PBS data format
        # loop csv file data row by row
        for column in csv.reader(io_string, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL):
            try:
                # process and create active components data
                if med_models.ActiveComponent.objects.filter(name=column[0]).count() == 0:
                    ac,  created = med_models.ActiveComponent.objects.get_or_create(name=column[0], name_ref=column[4])
                else:
                    ac = med_models.ActiveComponent.objects.get(name=column[0])
                
                # process SCH/PRN
                prn_value = column[32]
                if prn_value == "Yes":
                    med_type = const.MEDICATION_TYPE_VALUE__PRN
                else: 
                    med_type = const.MEDICATION_TYPE_VALUE__REGULAR
                
                dosageform=column[26]
                dosageform_ref = dosageform[:3].upper()
                if dosageform == "":
                    dosageform = "N/A"
                    dosageform_ref = "N/A"

                # create or update medication product data
                pharmacy_models.Product.objects.update_or_create(
                    unique_id=column[4],
                    title=column[1],
                    defaults = {
                        'title':column[1],
                        'unique_id':column[4],
                        'meta_data':'{"active_components": {"'+str(ac.id)+'":"'+ac.name+'"}, "SCH/PRN": "'+prn_value+'", "dosage_form": {"'+dosageform_ref+'": "'+dosageform+'"}}'
                    }
                )
                # create or update compound data
                compound, created = med_models.Compound.objects.update_or_create(
                    uid=column[4],
                    name=column[1],
                    defaults = {'source':source,'name':column[1],'dosage_form':column[26]}
                  )
                active_components = compound.active_components.all()
                compound.active_components.add(ac)
                compound.save()

                # store PRN data
                prn, created = models.CompoundExtraInformation.objects.get_or_create(compound=compound, name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE)
                prn.value = med_type
                prn.save()

            except Exception as error:
                # store error data row and error message in ImportHistory.details
                error_log = {'error_msg': str(error), 'error_data': column}
                error_logs.append(error_log)

        # finalise ImportHistory record
        with transaction.atomic():
            self.instance.status = "C"
            self.instance.details = error_logs
            self.instance.ended = timezone.now()
            self.instance.save()

        return super(CompoundImportHistoryForm, self).save(commit=commit)