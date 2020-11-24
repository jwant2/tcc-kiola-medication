import uuid
from django.db import models
from django_smartsearch.fields import JSONField
from django.conf import settings
from django.utils.encoding import force_text
from django_auditor.auditor import PermissionModelManager
from django.contrib.auth import get_user_model
from django_auditor.auditor import sudo

from kiola.kiola_med import models as med_models
from kiola.kiola_senses import models as senses
from . import utils, const
#from healthy_heart.models import Compound

# class MedCompound(models.Model):
#     name = models.CharField(max_length=100)

#     def __str__(self):
#         return self.name

# class MedCompoundTwo(models.Model):
#     name = models.CharField(max_length=100)

#     def __str__(self):
#         return self.name

# class Presc(models.Model):
#     name = models.CharField(max_length=100)

#     def __str__(self):
#         return self.name

class AdverseReactionType(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    def __str__(self):
        return self.name

class PatientAdverseReaction(models.Model):
    uid = models.CharField(max_length=100, default=str(uuid.uuid4()))
    subject = models.ForeignKey(senses.Subject, on_delete=models.PROTECT)
    substance = models.CharField(max_length=100, blank=False)
    reaction_type = models.ForeignKey(AdverseReactionType, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    reactions = models.TextField(blank=False)
    updated = models.DateTimeField(auto_now=True)    
    active = models.BooleanField(default=True)

    def __str__(self):
        return force_text("{}: {} - {} for {}").format(force_text(self.substance),
                                                   force_text(self.reaction_type),
                                                   force_text(self.reactions),
                                                   force_text(self.subject))

class MedicationAdverseReaction(models.Model):
  
    uid = models.CharField(max_length=100, default=str(uuid.uuid4()))
    compound = models.ForeignKey(med_models.Compound, on_delete=models.CASCADE)
    editor = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    reaction_type = models.ForeignKey(AdverseReactionType, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    reactions = models.TextField(blank=False)
    updated = models.DateTimeField(auto_now=True)    
    active = models.BooleanField(default=True)

    def __str__(self):
        return force_text("{}: {} updated by {}").format(force_text(self.compound),
                                                   force_text(self.reactions),
                                                   force_text(self.editor))

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

class TakingFrequency(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class ScheduledTaking(med_models.BaseTaking):
    TYPE_SHORT = const.TAKING_SCHEMA_TYPE__SCHEDULED
    formatter = utils.ScheduleTakingSchemaFormatter


    timepoint = models.ForeignKey(med_models.TakingTimepoint, on_delete=models.CASCADE)
    taking_time = models.TimeField(blank=False)
    start_date = models.DateField(blank=False)
    dosage = models.TextField(blank=False)
    strength = models.CharField(max_length=100)
    unit = models.ForeignKey(med_models.TakingUnit, on_delete=models.PROTECT)
    reminder = models.BooleanField(default=False)
    editor = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    clinic_scheduled = models.BooleanField(default=True)
    frequency = models.ForeignKey(TakingFrequency, on_delete=models.PROTECT)

    def as_dict(self):
        return {
                "pk": self.pk,
                "timepoint": self.timepoint.name,
                "taking_time": self.taking_time,
                "strength": self.strength,
                "dosage": self.dosage,
                "unit": self.unit.name,
                "start_date": self.start_date,
                "frequency": self.frequency.name,
                "editor": self.editor.username,
                "clinic_scheduled": self.clinic_scheduled,
                "reminder": self.reminder}

    def __str__(self):
        return force_text("{} {} {} {} {} from {} edited by {}").format(force_text(self.timepoint),
                                                   force_text(self.strength),
                                                   force_text(self.dosage),
                                                   force_text(self.unit),
                                                   force_text(self.frequency),                                                   
                                                   force_text(self.start_date),
                                                   force_text(self.editor))


class UserPreferenceConfigManager(PermissionModelManager):

    def set_value(self,key,value,user):

        with sudo():
            entries = self.filter(user=user)
        if len(entries)>0:
            entries[0].data[key] = value
            entries[0].save()
            created_index=False
        else:
            with sudo():
                model_index = self.create(user=user,data={key:value})
                created_index=True
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

    user  = models.OneToOneField(settings.AUTH_USER_MODEL,help_text="Owner of the index element. If the referenced model instance has a reference to Django's user model. It is most likely that these fields are equal.", on_delete=models.CASCADE)
    updated = models.DateTimeField(auto_now=True,help_text="Timestamp of last update to index element.")
    data = JSONField(default=element_default,help_text="The actual data of the index entry.",null=False,blank=False)



# class TccPrescriptionManager(PermissionModelManager):

#     # def prescribe(self, subject, prescriber, compound, reason, hint, taking, start,
#     #               end=None):
#     def prescribe(self):
#         print('htest')
#         return True

class CompoundExtraInformation(models.Model):
    
    compound = models.ForeignKey(med_models.Compound, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)
    value = models.TextField()

    def as_dict(self):
        return {
                "pk": self.pk,
                "compound": self.compound.name,
                "name": self.name,
                "value": self.value
        }

    def __str__(self):
        return force_text("{} - {} for {}").format(force_text(self.name),
                                                   force_text(self.value),
                                                   force_text(self.compound.name))