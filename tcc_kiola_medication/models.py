import json
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils import formats
from django.utils.encoding import force_text
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext_noop
from django_auditor.auditor import PermissionModelManager, sudo
from django_smartsearch.fields import JSONField

from kiola.kiola_med import const as med_const
from kiola.kiola_med import models as med_models
from kiola.kiola_med import utils as med_utils
from kiola.kiola_pharmacy import models as pharmacy_models
from kiola.kiola_senses import models as senses
from kiola.utils import service_providers
from kiola.utils.authorization import track_model
from kiola.utils.commons import get_system_user

from . import const, utils


class AdverseReactionType(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.name


track_model(AdverseReactionType)


class PatientAdverseReaction(models.Model):
    uid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(senses.Subject, on_delete=models.PROTECT)
    substance = models.CharField(max_length=100, blank=False)
    reaction_type = models.ForeignKey(AdverseReactionType, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    reactions = models.TextField(blank=False)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return force_text("{}: {} - {} for {}").format(
            force_text(self.substance),
            force_text(self.reaction_type),
            force_text(self.reactions),
            force_text(self.subject),
        )


class MedicationAdverseReaction(models.Model):

    uid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    compound = models.ForeignKey(med_models.Compound, on_delete=models.CASCADE)
    editor = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    reaction_type = models.ForeignKey(AdverseReactionType, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    reactions = models.TextField(blank=False)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return force_text("{}: {} updated by {}").format(
            force_text(self.compound),
            force_text(self.reactions),
            force_text(self.editor),
        )

    def as_dict(self):
        return {
            "uid": self.uid,
            "compound": self.compound.name,
            "compoundId": self.compound.pk,
            "reactionType": self.reaction_type.name,
            "reactions": self.reactions,
            "editor": self.editor.username,
            "created": self.created,
            "updated": self.updated,
            "active": self.active,
        }


track_model(MedicationAdverseReaction)


class TakingFrequency(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.name


track_model(TakingFrequency)


class ScheduledTaking(med_models.BaseTaking):
    TYPE_SHORT = const.TAKING_SCHEMA_TYPE__SCHEDULED
    formatter = utils.ScheduleTakingSchemaFormatter

    timepoint = models.ForeignKey(med_models.TakingTimepoint, on_delete=models.CASCADE)
    taking_time = models.TimeField(blank=False)
    start_date = models.DateField(blank=False)
    end_date = models.DateField(blank=True, null=True)
    dosage = models.CharField(max_length=100)
    strength = models.CharField(max_length=100)
    hint = models.TextField()  # taking_hint
    unit = models.ForeignKey(med_models.TakingUnit, on_delete=models.PROTECT)
    reminder = models.BooleanField(default=False)
    editor = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    clinic_scheduled = models.BooleanField(default=True)
    frequency = models.ForeignKey(TakingFrequency, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    def as_dict(self):
        return {
            "pk": self.pk,
            "timepoint": self.timepoint.name,
            "taking_time": self.taking_time,
            "strength": self.strength,
            "dosage": self.dosage,
            "unit": self.unit.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "hint": self.hint,
            "frequency": self.frequency.name,
            "editor": self.editor.username,
            "clinic_scheduled": self.clinic_scheduled,
            "created": self.created,
            "updated": self.updated,
            "active": self.active,
            "reminder": self.reminder,
        }

    def __str__(self):
        return force_text("{} {} {} {} {}").format(
            force_text(self.taking_time.strftime("%H:%M")),
            force_text(self.strength),
            force_text(self.dosage),
            force_text(self.unit),
            force_text(self.frequency),
        )

    def get_displayable(self):
        return force_text("{} {} {} - {}/{}/{}").format(
            force_text(self.frequency),
            force_text(self.timepoint.name),
            force_text(self.taking_time),
            force_text(self.strength),
            force_text(self.dosage),
            force_text(self.unit),
        )


track_model(ScheduledTaking)


class UserPreferenceConfigManager(PermissionModelManager):
    def set_value(self, key, value, user):

        with sudo():
            entries = self.filter(user=user)
        if len(entries) > 0:
            entries[0].data[key] = value
            entries[0].save()
            created_index = False
        else:
            with sudo():
                model_index = self.create(user=user, data={key: value})
                created_index = True
        return created_index

    def get_value(self, key, user):

        model_index = self._load_object(user)
        if model_index is None:
            return None
        value = model_index.data.get(key)

        return value

    def _load_object(self, user):

        try:
            model_index = self.get(user=user)
        except UserPreferenceConfig.DoesNotExist:
            return None
        return model_index


def element_default():
    # PostgreSQL JSONField requires us to have
    # a callable function as default
    return {}


class UserPreferenceConfig(models.Model):
    objects = UserPreferenceConfigManager()

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        help_text="Owner of the index element. If the referenced model instance has a reference to Django's user model. It is most likely that these fields are equal.",
        on_delete=models.CASCADE,
    )
    updated = models.DateTimeField(
        auto_now=True, help_text="Timestamp of last update to index element."
    )
    data = JSONField(
        default=element_default,
        help_text="The actual data of the index entry.",
        null=False,
        blank=False,
    )


track_model(UserPreferenceConfig)


class CompoundExtraInformation(models.Model):

    compound = models.ForeignKey(med_models.Compound, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    value = models.TextField()

    class Meta:
        unique_together = (("compound", "name"),)

    def as_dict(self):
        return {
            "pk": self.pk,
            "compound": self.compound.name,
            "name": self.name,
            "value": self.value,
        }

    def __str__(self):
        return force_text("{} - {} for {}").format(
            force_text(self.name),
            force_text(self.value),
            force_text(self.compound.name),
        )


track_model(CompoundExtraInformation)


class PrescriptionExtraInformation(models.Model):

    prescription = models.ForeignKey(med_models.Prescription, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    value = models.TextField()

    class Meta:
        unique_together = (("prescription", "name"),)

    def as_dict(self):
        return {
            "pk": self.pk,
            "prescription": self.prescription,
            "name": self.name,
            "value": self.value,
        }

    def __str__(self):
        return force_text("{} - {} for {}").format(
            force_text(self.name), force_text(self.value), force_text(self.prescription)
        )


track_model(PrescriptionExtraInformation)


class MedicationRelatedHistoryDataManager(PermissionModelManager):
    def add_data_change_record(self, related_object, request_data):
        ct = ContentType.objects.get(model=related_object._meta.model_name)
        object_id = related_object.id
        record = self.create(content_type=ct, object_id=object_id, data=request_data)
        return record

    def get_history_data(self, data_object):
        ct = ContentType.objects.get(model=data_object._meta.model_name)
        object_id = data_object.id
        qs = self.filter(content_type=ct, object_id=object_id)
        return qs


class MedicationRelatedHistoryData(models.Model):

    objects = MedicationRelatedHistoryDataManager()

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text=_("Model type of the target object. "),
    )  ## Compound/Prescription/MedAdeverseReaction/etc..
    object_id = models.IntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    created = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp of data created."
    )
    data = JSONField(
        default=element_default,
        help_text="Data of changes to content_object.",
        null=False,
        blank=False,
    )

    def as_dict(self):
        return {
            "pk": self.pk,
            "content_type": self.content_type,
            "content_object": self.content_object,
            "data": self.data,
            "created": self.created,
        }

    def __str__(self):
        return force_text("{} - {} for {}").format(
            force_text(self.content_object),
            force_text(self.data),
            force_text(self.created),
        )


track_model(MedicationRelatedHistoryData)


def drug_search(q, by_id=False, source=None):
    imports = pharmacy_models.ImportHistory.objects.all().order_by("-pk")
    if len(imports) > 0:
        if imports[0].status != "C":
            raise service_providers.ServiceNotAvailable()
    data = []
    if not source:
        source = med_models.CompoundSource.objects.get(default=True)
    # only returns current version of compounds
    filter_params = [Q(meta_data__contains=f'"version": "{source.version}"')]
    if by_id:
        q = q.strip().lower()
        filter_params = [Q(unique_id=q)]
    else:
        q = q.strip().lower()
        if len(q) == 0:
            return []
        qparts = q.split(" ")
        for qpart in qparts:
            qpart = qpart.strip()
            if qpart != "":
                filter_params.append(Q(title__icontains=qpart))
    count = 1
    for product in pharmacy_models.Product.objects.filter(*filter_params):
        meta = json.loads(product.meta_data)

        data.append(
            {
                "title": product.title,
                "unique_id": product.unique_id,
                "main_indications": meta.get("main_indication", {"1": None}),
                "active_components": meta.get("active_components", "-"),
                "dosage_form": meta.get("dosage_form", "-"),
                "source": meta.get("source", None),
                "SCH/PRN": meta.get("SCH/PRN", None),
                "count": count,
            }
        )
        count += 1
    return data


service_providers.service_registry.register(name="drug_search", function=drug_search)


class MedicationType(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()


class TCCPrescriptionManager(PermissionModelManager):
    def prescribe(
        self,
        subject,
        prescriber,
        compound,
        reason,
        hint,
        start,
        dosage,
        strength,
        unit,
        med_type,
        end=None,
    ):

        # check if prescription exists (respect status active only)
        # set it to inactive/replaced
        replaced = None
        existing = self.filter(
            subject=subject,
            compound=compound,
            status__name=med_const.PRESCRIPTION_STATUS__ACTIVE,
        )
        if len(existing) > 0:
            existing = existing[0]
            med_models.PrescriptionEvent.objects.create(
                prescription=existing,
                timepoint=now(),
                triggered_by=get_system_user(),
                etype=med_models.PrescriptionEventType.objects.get(
                    name=med_const.EVENT_TYPE__REPLACED
                ),
            )
            existing.status = med_models.PrescriptionStatus.objects.get(
                name=med_const.PRESCRIPTION_STATUS__INACTIVE
            )
            replaced = existing

        prescription = self.create(
            compound=compound,
            status=med_models.PrescriptionStatus.objects.get(
                name=med_const.PRESCRIPTION_STATUS__ACTIVE
            ),
            subject=subject,
            taking_reason=reason,
            taking_hint=hint,
            dosage=dosage,
            strength=strength,
            unit=unit,
            medication_type=med_type,
            editor=prescriber,
        )
        prescription.save()

        params = utils.prescription_event__params()
        # add start end stop event

        med_models.PrescriptionEvent.objects.create(
            prescription=prescription,
            timepoint=start,
            etype=med_models.PrescriptionEventType.objects.get(
                name=med_const.EVENT_TYPE__PRESCRIBED
            ),
            **params,
        )

        # add the original create time

        med_models.PrescriptionEvent.objects.create(
            prescription=prescription,
            timepoint=now(),
            etype=med_models.PrescriptionEventType.objects.get(
                name=med_const.EVENT_TYPE__ADDED
            ),
            **params,
        )

        if end:

            med_models.PrescriptionEvent.objects.create(
                prescription=prescription,
                timepoint=end,
                etype=med_models.PrescriptionEventType.objects.get(
                    name=med_const.EVENT_TYPE__END
                ),
                **params,
            )

        med_models.PrescriptionSchema.objects.create(
            taking_schema=med_models.TakingSchema.objects.create(),
            prescription=prescription,
        )
        prescription.save()

        if replaced:
            replaced.replaced = True
            replaced.save()
            med_models.PrescriptionProfileRelation.objects.remove_and_update(
                remove=replaced, replaceby=prescription
            )

        return prescription, replaced


class TCCPrescription(med_models.Prescription):
    objects = TCCPrescriptionManager()
    priviledged = models.Manager()
    editor = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    takings = models.ManyToManyField(ScheduledTaking, related_name="takings_set")
    dosage = models.TextField(blank=True)
    strength = models.CharField(max_length=100, blank=True)
    unit = models.ForeignKey(med_models.TakingUnit, on_delete=models.PROTECT)
    medication_type = models.ForeignKey(MedicationType, on_delete=models.PROTECT)


track_model(TCCPrescription)
