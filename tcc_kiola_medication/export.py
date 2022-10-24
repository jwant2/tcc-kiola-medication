from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from tcc_kiola_common.const import CIRCLE_TYPE__LOCAL_SITE
from tcc_kiola_common.export import CustomAdminModelExport

from kiola.kiola_export import data_sources
from kiola.kiola_senses import const as senses_const
from kiola.kiola_senses import models as senses_models


class TCCSubjectPrescriptionDataExport(CustomAdminModelExport):
    RELTATED_FIELD_NAMES = []
    EXTRA_LIST_FIELDS = [
        "login__first_name",
        "login__last_name",
        "login__audience__circle__name",
    ]

    def name(self):
        return "TCC Subject Prescription Data Export"

    def description(self):
        return "TCC Subject Prescription Data Export"

    def queryset(self, qs, parameters):
        qs = qs.filter(
            subjectstatus__status__level=senses_const.SUBJECT_STATUS_LEVEL__ACTIVE,
            login__audience__circle__circle_type__name=CIRCLE_TYPE__LOCAL_SITE,
        ).annotate(
            entered_prescriptions=Count("prescription"),
        )
        return qs, ["entered_prescriptions"]


ct = ContentType.objects.get(
    model=senses_models.Subject()._meta.model_name,
    app_label=senses_models.Subject()._meta.app_label,
)
data_sources.data_sources.register(TCCSubjectPrescriptionDataExport(content_type=ct))
