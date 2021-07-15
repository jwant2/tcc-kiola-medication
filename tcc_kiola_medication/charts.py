
import copy
import math
from kiola.kiola_senses.models.base import IN_PROGRESS
import numpy
import datetime
from operator import itemgetter
import itertools
from random import randint

from colour import Color

from django.utils.translation import ugettext_lazy as _, get_language, ugettext_noop
# from django.core import serializers
from django.utils import formats, dateformat, timezone
from django.urls import reverse
from django.db.models import Q, Prefetch, Subquery, OuterRef, F
from django.utils.encoding import force_text

from kiola.kiola_senses import models as senses
from kiola.kiola_senses.models import  base
from kiola.kiola_senses import const as senses_const
from kiola.kiola_charts import charts as base_charts
from kiola.cares import charts as cares_charts
from kiola.cares import const as cares_const
from kiola.cares import modules as cares_modules
from kiola.cares import models as cares
from kiola.utils import serializer
from kiola.kiola_charts import utils as charts_utils
from kiola.kiola_charts import const as charts_const
from kiola.kiola_med import const as med_const, models as med_models
from . import const, models


class TCCMedicationComplianceChart(cares_charts.ChartBase):

    category = const.CHART_CATEGORY__TCC_MEDICATION

    show_on_dashboard = True

    plots = [base_charts.TimePlot, ]

    series = [
        const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_TAKE,
        const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_UNDO,
        const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_NOT_TAKE,
      ]

    chart_options = {"plotOptions": {
        "line": {
            "marker": {
                "enabled": True,
            },
        },
    },
    }
    chart_options.update(
        {"yAxis": {
            'type': 'datetime',
            "labels": {"enabled": True, "format": '{value:%H:%M}'},
            "title": {
                "text": _("Medication Taken Time"),
            },
          },
        "xAxis": {
          'type': 'datetime',
          "labels": {"enabled": True},
        },
    })

    series_options = [{
        "name": f'Medication compliance {_(const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_TAKE)}',
        "lineWidth": 0,
        "color": "#87B87F",
        "marker": {
            "symbol": u'triangle',
            "radius": charts_const.CHART__DEFAULT_MARKER_RADIUS,
            "enabled": True},
        "zIndex": 10,
        "turboThreshold": 2000,

    },
    {
        "name": f'Medication compliance {_(const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_UNDO)}',
            "lineWidth": 0,
            "color": "#FFB752",
            "marker": {
                "symbol": u'square',
            "radius": charts_const.CHART__DEFAULT_MARKER_RADIUS,
            "enabled": True},
            "zIndex": 11,
            "turboThreshold": 2000,

    },
    {
        "name": f'Medication compliance {_(const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_NOT_TAKE)}',
            "lineWidth": 0,
            "color": "red",
            "marker": {
                "symbol": u'triangle-down',
            "radius": charts_const.CHART__DEFAULT_MARKER_RADIUS,
            "enabled": True},
            "zIndex": 11,
            "turboThreshold": 2000,

    },
    ]


    def get(self, subject, which, period, ajax=False, data_filters={}):

        plot = super(TCCMedicationComplianceChart, self).get(subject, which, period, ajax, data_filters)
        chart_options = copy.deepcopy(self.chart_options)

        flt = {'parent__started__range': period, }
        flt.update(data_filters)
        # get chart data for each series
        for counter, series in enumerate(self.series):
            observations = (
                senses.EnumerationObservation.objects.filter(
                  parent__profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION,
                  started__range=period,
                  profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION, 
                  value=series,
                  status=base.COMPLETED, # filter invalid observation
                  subject=subject).order_by("started") 
                  .annotate(schedule=Subquery(senses.DateTimeSimpleObservation.accepted.filter(parent__pk=OuterRef('parent__pk'), 
                                  profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_TIME
                                  ).values('value')
                            )
                  )
                  .annotate(prescr_id=Subquery(senses.TextObservation.accepted.filter(parent__pk=OuterRef('parent__pk'), 
                                  profile__name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_MEDICATION_ID, 
                                  ).values('value')
                            )   
                  )
                      
            )

            chart_data = []
            for observation in observations:
                try: 
                    compound = models.TCCPrescription.objects.get(pk=observation.prescr_id).compound.name
                except models.TCCPrescription.DoesNotExist:
                    compound = None # this means observation data is invalid
                pointdata = {"x": observation.parent.started.replace(hour=0, minute=0, second=0),
                             "y": observation.parent.started,
                             "compound": compound,
                             "schedule": observation.schedule,
                             "actual": observation.parent.started,
                             "action": observation.value.upper()
                            }
                chart_data.append(pointdata)

            series_options = copy.deepcopy(self.series_options[counter])
            series_options.update({"tooltip": {
                                  "useHTML": True,
                                  "pointFormat": '{point.compound}: <span style="color:{series.color}">{point.action}</span> <br>Schedule time: {point.schedule:%H:%M} ',
                                  "crosshairs": True,
                                  "headerFormat": "<b>{point.y:%d/%m/%Y %H:%M}</b><br>"
                                  },
                                  "name": _(series).upper(),
            })
            plot.addSeries(chart_data, series_options)

        plot.updateOptions(chart_options)
        return plot


charts_utils.chart_registry.register(TCCMedicationComplianceChart)
cares_modules.AllChartsModule.setoption(const.CHART_CATEGORY__TCC_MEDICATION, "h=200&ldrag=1")
