

from . import models, const 
from kiola.kiola_med import utils as med_utils, models as med_models
from kiola.kiola_med.templatetags import med as med_tags
from kiola.utils import service_providers

from django.utils.translation import ugettext_lazy as _
from datetime import datetime
from django.utils.encoding import force_text

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
        current_compound_source = med_models.CompoundSource.objects.get(default=True, name=compound.source.name)
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
                new_compound = drugs[0]
                context["compound_newer"] = {}
                context["compound_newer"]["title"] = new_compound["title"]
                context["compound_newer"]["unique_id"] = new_compound["unique_id"]
                context["compound_newer"]["main_indications"] = list(new_compound["main_indications"].values())[0]
                context["compound_newer"]["active_components"] = u", ".join(sorted(new_compound["active_components"].values()))
                context["compound_newer"]["dosage_form"] = list(new_compound["dosage_form"].values())[0]


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
