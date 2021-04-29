from datetime import datetime

from django.core import exceptions as djexceptions
from django.db.models import F
from django.utils.encoding import force_text

from tcc_hf import utils as hf_utils

from kiola.kiola_clients import signals
from kiola.kiola_med import models as med_models
from kiola.kiola_med import utils as med_utils
from kiola.kiola_med.templatetags import med as med_tags
from kiola.utils import const as kiola_const
from kiola.utils import service_providers
from kiola.utils.commons import get_system_user

from . import const, models


def value_is_not_none(item):
    _, value = item
    return value is not None

def filter_none_values(items):
    return filter(value_is_not_none, items)


class PaginationHandlerMixin(object):
    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        else:
            pass
        return self._paginator

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset,
                   self.request, view=self)
                   
    def get_paginated_response(self, data):
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)


def set_default_user_pref_med_time_values(user):
    models.UserPreferenceConfig.objects.set_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, const.MEDICATION_TIMES_DEFAULT_VALUES, user)

class ScheduleTakingSchemaFormatter(med_utils.TakingSchemaFormatter):
    
    seperator = " / "

    def format(self, language=None):
        out = []
        for taking in self.schema.takings.all().order_by('orderedtaking__order'):

            unit = taking.scheduledtaking.unit.name
            frequency = taking.scheduledtaking.frequency.name
            dosage = taking.scheduledtaking.dosage
            taking_time = taking.scheduledtaking.taking_time
            strength = taking.scheduledtaking.strength
            text = f"{taking_time} {strength} {dosage} {unit} {frequency}"
            out.append(text)
        out = self.seperator.join(out)
        return out


class TakingSchemaScheduled(med_utils.TakingSchemaBase):
    def __init__(self, timepoint, taking_time, start_date, dosage, strength, unit, reminder, editor, clinic_scheduled, frequency):
        timepoint = timepoint
        taking_time = taking_time
        start_date = start_date
        dosage = dosage
        strength = strength
        unit = unit
        reminder = reminder
        editor = editor
        clinic_scheduled = clinic_scheduled
        frequency = frequency


    def get(self):
        return {
                "timepoint": self.timepoint,
                "taking_time": self.taking_time,
                "strength": self.strength,
                "dosage": self.dosage,
                "unit": self.unit.name,
                "start_date": self.start_date,
                "frequency": self.frequency,
                "editor": self.editor,
                "clinic_scheduled": self.clinic_scheduled,
                "reminder": self.reminder
                }

def user_preference_value_mapping(data):
    mapping = {}
    for item in data.values():
        time = datetime.strptime(item['actualTime'], "%H:%M")
        mapping[item['type']] = force_text(time.time())
    return mapping

# replace from kiola_med.templatetags.med.render_sis_compound_info  for adding PRN info
def tcc_render_sis_compound_info(context, compound_id, compound_source=None):
    try:
        params = {"uid":compound_id}
        if compound_source:
            params.update({"source__pk":compound_source})
        compound = med_models.Compound.objects.filter(**params).order_by('pk').last()
        current_compound_source = med_models.CompoundSource.objects.get(default=True)
        context["current_compound_source"] = current_compound_source
        if compound.source.pk != current_compound_source.pk:
            context["compound_newer_available"] = True
            try:
                new_compound = med_models.Compound.objects.get(uid=compound_id, source=current_compound_source)

                context["compound_newer"] = {}
                context["compound_newer"]["source_version"] = current_compound_source.version
                context["compound_newer"]["title"] = new_compound.name
                context["compound_newer"]["unique_id"] = compound_id
                context["compound_newer"]["main_indications"] = u", ".join(new_compound.indications.all().values_list("name", flat=True))
                context["compound_newer"]["active_components"] = u", ".join(new_compound.active_components.all().values_list("name", flat=True).order_by("name"))
                context["compound_newer"]["dosage_form"] = new_compound.dosage_form
            except med_models.Compound.DoesNotExist:
                drug_search = service_providers.service_registry.search("drug_search")
                drugs = drug_search(q=compound_id, by_id=True)
                if len(drugs) > 0:
                    new_compound = drugs[0]
                    context["compound_newer"] = {}
                    context["compound_newer"]["title"] = new_compound["title"]
                    context["compound_newer"]["unique_id"] = new_compound["unique_id"]
                    context["compound_newer"]["main_indications"] = list(new_compound["main_indications"].values())[0]
                    context["compound_newer"]["active_components"] = u", ".join(sorted(new_compound["active_components"].values()))
                    context["compound_newer"]["dosage_form"] = list(new_compound["dosage_form"].values())[0]
                else:
                    context["compound_newer_available"] = False


        context["title"] = compound.name
        context["unique_id"] = compound_id
        context["main_indications"] = u", ".join(compound.indications.all().values_list("name", flat=True))
        context["active_components"] = u", ".join(compound.active_components.all().values_list("name", flat=True).order_by("name"))
        context["dosage_form"] = compound.dosage_form
        context["compound_source"] = compound.source
    except med_models.Compound.DoesNotExist:
        drug_search = service_providers.service_registry.search("drug_search")
        drugs = drug_search(q=compound_id, by_id=True)
        compound = drugs[0]
        context["title"] = compound["title"]
        context["unique_id"] = compound["unique_id"]
        context["main_indications"] = list(compound["main_indications"].values())[0]
        context["active_components"] = u", ".join(sorted(compound["active_components"].values()))
        context["dosage_form"] = list(compound["dosage_form"].values())[0]
    prn = models.CompoundExtraInformation.objects.filter(compound=compound, name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE).last()
    if prn:
        context["prn"] = prn.value
    return context

med_tags.register.inclusion_tag('tcc_sis_search_result.html'   , takes_context=True)(tcc_render_sis_compound_info)


class TCCAdapter(med_utils.CompoundAdapterBase):

    def get_or_create(self, compound_id):
        from . import models

        # FIXME:cgo: we should filter for uid only here?
        # how to check if compound source is of same type?
        # -> use same name or add new attribute compound source type?
        compounds = self.manager.filter(uid=compound_id,
                                        source=self.source)

        # if compound already exists don't create a new one
        # FIXME:cgo: this should move into a Compound Source specific adapter class
        # right now only SIS DBs are supported
        created = False
        if len(compounds) == 0:
            created = True
            drug_search = service_providers.service_registry.search("drug_search")
            drugs = drug_search(q=compound_id, by_id=True)
            if len(drugs) == 0:
                raise ValueError("No drug found matching product ID '%s'" % compound_id)
            product = drugs[0]
            compound, created = self.manager.get_or_create(
                uid=compound_id,
                source=self.source,
                defaults={
                    'dosage_form_ref': list(product["dosage_form"].keys())[0],
                    'dosage_form': list(product["dosage_form"].values())[0],
                    'name': product["title"],
                    'registration_number': product.get("znumm", None)
                }
            )

            for unique_id, comp in product["active_components"].items():
                if comp:
                    active_component, created = med_models.ActiveComponent.objects.get_or_create(name=comp,
                                                                                             name_ref=compound_id)
                    compound.active_components.add(active_component)

            # store PRN data
            prn_value = product.get("SCH/PRN", None)
            prn = None
            if prn_value:
                if prn_value == "Yes":
                    med_type = const.MEDICATION_TYPE_VALUE__REGULAR
                else: 
                    med_type = const.MEDICATION_TYPE_VALUE__PRN
                prn, created = models.CompoundExtraInformation.objects.get_or_create(compound=compound, name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE)
                if created:
                    prn.value = med_type
                    prn.save()

        elif len(compounds) > 1:
            raise djexceptions.MultipleObjectsReturned("Found more than one compound, matching id and source")
        else:
            compound = compounds[0]

        return compound, created


def filter_schedule_for_given_date(given_date, qs):
    '''
    Return schedules that should be taken on the given date
    '''
    filtered_ids = []
    current_date = given_date.date()
    for taking in qs:
        date =  taking.start_date
        if taking.frequency.name == const.TAKING_FREQUENCY_VALUE__ONCE \
            and current_date == date:
            filtered_ids.append(taking.id)
        elif taking.frequency.name == const.TAKING_FREQUENCY_VALUE__DAILY:
            filtered_ids.append(taking.id)
        elif taking.frequency.name == const.TAKING_FREQUENCY_VALUE__WEEKLY \
            and current_date.weekday() == date.weekday():
            filtered_ids.append(taking.id)
        elif taking.frequency.name == const.TAKING_FREQUENCY_VALUE__FORTNIGHTLY \
            and (current_date - date).days % 14 == 0 and current_date.weekday() == date.weekday():
            filtered_ids.append(taking.id)
        elif taking.frequency.name == const.TAKING_FREQUENCY_VALUE__MONTHLY \
            and (current_date - date).days % 30 == 0:
            filtered_ids.append(taking.id)
    return models.ScheduledTaking.objects.filter(id__in=filtered_ids).annotate(prescr_id=
                F('takingschema__prescriptionschema__prescription')
    )



def send_medication_reminder_notification(subject, taking, time, compound_name):
    # send out medication reminder notification to patient
    feedback_body = const.MEDICATION_REMINDER__MESSAGE_BODY % (compound_name, time)
    message = hf_utils.create_feedback_FCM(get_system_user(), subject, feedback_body)
    data = {
      "type": "feedback",
      "feedbackId": message.id,
      "text": feedback_body
    }
    signal_results = signals.sensor_event_created.send_robust(
        taking,
        data=data,
        subject="TCC Cardiac - Medication Reminder",
        recipient=subject.login,
        valid_in_hours=24,
        backend="FCM_NO_ENCRYPTION",
        mime_type=kiola_const.MIME_TYPE__APPLICATION_JSON,
    )
