import uuid
from django.db import models

#from healthy_heart.models import *

import kiola.kiola_med.models
from kiola.kiola_med.models import *
from django.contrib.auth import get_user_model

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
    compound = models.ForeignKey(Compound, on_delete=models.CASCADE)
    editor = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    reactions = models.TextField(blank=False)
    updated = models.DateTimeField(auto_now=True)    
    active = models.BooleanField(default=True)

    def __str__(self):
        return force_text("{}: {} updated by {}").format(force_text(self.compound),
                                                   force_text(self.reactions),
                                                   force_text(self.editor))


    # def save(self, *args, **kwargs):
    #     self.substance = self.compound.name
    #     super(MedicationAdverseReaction, self).save(args, kwargs)