

from . import models, const 
from kiola.kiola_med import utils as med_utils
from django.utils.translation import ugettext_lazy as _

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