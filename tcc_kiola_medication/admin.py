from django.contrib import admin

from kiola.utils.admin import KIOLAAdmin
from . import models

class AdverseReactionTypeAdmin(KIOLAAdmin):
    list_display = ["name"]

admin.site.register(models.AdverseReactionType, AdverseReactionTypeAdmin)

class MedicationAdverseReactionAdmin(KIOLAAdmin):
    list_display = ["created", "compound", "reaction_type", "reactions" ,"editor", "active"]

admin.site.register(models.MedicationAdverseReaction, MedicationAdverseReactionAdmin)

class ScheduledTakingAdmin(KIOLAAdmin):
    list_display = ["pk", "timepoint", "taking_time", "start_date", "editor", "clinic_scheduled"]

admin.site.register(models.ScheduledTaking, ScheduledTakingAdmin)

class UserPreferenceConfigAdmin(KIOLAAdmin):
    list_display = ["user", "updated", "data"]

admin.site.register(models.UserPreferenceConfig, UserPreferenceConfigAdmin)

class CompoundExtraInformationAdmin(KIOLAAdmin):
    list_display = ["compound", "name", "value"]

admin.site.register(models.CompoundExtraInformation, CompoundExtraInformationAdmin)