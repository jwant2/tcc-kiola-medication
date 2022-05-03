import json
from datetime import datetime, timedelta

from dateutil import parser
from django.apps import apps
from django.db.models import Avg, Count, F, Max, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Trunc
from django.template import Context, loader
from django.utils.safestring import mark_safe
from django.utils.timezone import get_current_timezone
from django.utils.translation import get_language, ugettext
from django.utils.translation import ugettext_lazy as _

if apps.is_installed("django_bootgrid"):
    from django_bootgrid import bootgrid
else:
    import kiola.kiola_bootgrid.bootgrid as bootgrid

from kiola.kiola_med import const as med_const
from kiola.kiola_senses import models as senses_models

from . import const, models


class MedicationAdherenceOverview(object):
    model = senses_models.Observation
    title = _("Medication taken")
    template_name = "list/med_table.html"
    use_full_objects = True

    field_colors = {
        "take": "success",  # green
        "not_take": "danger",  # red
        "undo": "warning",  # yellow
    }

    def __init__(self, request, start=None, stop=None):
        self.request = request
        if start and stop:
            self.start = start
            self.stop = stop
        else:
            self.stop = datetime.now().astimezone(get_current_timezone())
            self.start = self.stop - timedelta(days=7)

    def render(self):
        t = loader.get_template(self.template_name)
        schedules = self._get_active_schedule(self.request)
        days = (self.stop - self.start).days
        headers = [""]
        for i in range(0, days):
            headers.append((self.start + timedelta(days=i + 1)).strftime("%d/%m"))
        data = []
        for schedule in schedules:
            row_data = []
            row_data.append(
                dict(
                    value=(
                        "%s (%s)" % (schedule.compound_name, schedule.get_displayable())
                    ),
                    cell_class="col-md-4",
                )
            )
            for i in range(0, days):
                row_data.append(dict(color_class="", value=""))
            schedule_data = self._get_obs_data(
                self.request, schedule.pk, self.start, self.stop
            )
            for item in schedule_data:
                idx = self._check_date_index(item.action_date)
                if idx < 0:
                    continue
                cell_color = self.field_colors.get(item.action, "")
                # format action time format, or use parent.started for morning/afternoon/etc..
                try:
                    time = parser.parse(item.action_time).time().strftime("%H:%M")
                except:
                    time = (
                        item.parent.started.astimezone(get_current_timezone())
                        .time()
                        .strftime("%H:%M")
                    )
                row_data[idx] = dict(
                    color_class=f"{cell_color} col-md-1",
                    value=time if item.action != "undo" else "-",
                )
            data.append(row_data)

        c = Context(
            dict(
                title=self.title,
                request=self.request,
                headers=headers,
                data=data,
            )
        )
        return t.render(c)

    def _check_date_index(self, value) -> int:
        value_date = parser.parse(value).date()
        if value_date < self.start.date() or value_date > self.stop.date():
            return -1
        index = (value_date - self.start.date()).days
        # first column reserve for schedule info
        if index <= 0:
            return -1
        return index

    def _get_active_schedule(self, request, count_only=False, **kwargs):
        subject_uid = self.request.subject_uid
        schedules = (
            models.ScheduledTaking.objects.prefetch_related(
                "takings_set", "takings_set__compound"
            )
            .filter(
                takings_set__subject__uuid=subject_uid,
                takings_set__status__name=med_const.PRESCRIPTION_STATUS__ACTIVE,
                active=True,
            )
            .annotate(prescr_id=F("takings_set__id"))
            .annotate(compound_name=F("takings_set__compound__name"))
        )
        return schedules

    def _get_obs_data(
        self, request, schedule_id, start=None, stop=None, count_only=False, **kwargs
    ):
        subject_uid = self.request.subject_uid
        observations = (
            senses_models.TextObservation.objects.filter(
                parent__profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION,
                profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ID,
                status=senses_models.base.COMPLETED,  # filter invalid observation
                subject__uuid=subject_uid,
                value=schedule_id,
            )
            .select_related("parent")
            .order_by("started")
            .annotate(
                schedule_time=Subquery(
                    senses_models.DateTimeSimpleObservation.accepted.filter(
                        parent__pk=OuterRef("parent__pk"),
                        profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_TIME,
                    ).values("value")
                )
            )
            .annotate(
                action_time=Subquery(
                    senses_models.TextObservation.accepted.filter(
                        parent__pk=OuterRef("parent__pk"),
                        profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ACTION_TIME,
                    ).values("value")
                )
            )
            .annotate(
                action_date=Subquery(
                    senses_models.TextObservation.accepted.filter(
                        parent__pk=OuterRef("parent__pk"),
                        profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ACTION_DATE,
                    ).values("value")
                )
            )
            .annotate(
                action=Subquery(
                    senses_models.EnumerationObservation.accepted.filter(
                        parent__pk=OuterRef("parent__pk"),
                        profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION,
                    ).values("value")
                )
            )
        )
        if start and stop:
            observations.filter(parent__started__range=[start, stop])
        if count_only:
            return observations.count()
        return observations
