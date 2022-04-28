from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from kiola.kiola_pharmacy import models as pharmacy_models
from kiola.utils.admin import KIOLAAdmin

from . import forms, models


class AdverseReactionTypeAdmin(KIOLAAdmin):
    list_display = ["name"]


admin.site.register(models.AdverseReactionType, AdverseReactionTypeAdmin)


class MedicationAdverseReactionAdmin(KIOLAAdmin):
    list_display = [
        "created",
        "compound",
        "reaction_type",
        "reactions",
        "editor",
        "active",
    ]


admin.site.register(models.MedicationAdverseReaction, MedicationAdverseReactionAdmin)


class ScheduledTakingAdmin(KIOLAAdmin):
    list_display = [
        "pk",
        "timepoint",
        "taking_time",
        "start_date",
        "editor",
        "clinic_scheduled",
    ]


admin.site.register(models.ScheduledTaking, ScheduledTakingAdmin)


class UserPreferenceConfigAdmin(KIOLAAdmin):
    list_display = ["user", "updated", "data"]


admin.site.register(models.UserPreferenceConfig, UserPreferenceConfigAdmin)


class CompoundExtraInformationAdmin(KIOLAAdmin):
    list_display = ["compound", "name", "value"]


admin.site.register(models.CompoundExtraInformation, CompoundExtraInformationAdmin)


class PrescriptionExtraInformationAdmin(KIOLAAdmin):
    list_display = ["prescription", "name", "value"]


admin.site.register(
    models.PrescriptionExtraInformation, PrescriptionExtraInformationAdmin
)


class MedicationRelatedHistoryDataAddmin(KIOLAAdmin):
    list_display = ["content_object", "data", "created"]


admin.site.register(
    models.MedicationRelatedHistoryData, MedicationRelatedHistoryDataAddmin
)


class CompoundImport(pharmacy_models.ImportHistory):
    class Meta:
        proxy = True
        verbose_name = _("Compound Import")
        verbose_name_plural = _("Compound Import")


class CompoundImportAdmin(KIOLAAdmin):
    # change_form_template = "admin/test_form.html"
    list_filter = ("status", "started", "ended")

    def get_status(self, instance):
        if instance.status == "F":
            color = "red"
            message = "Failed"
        elif instance.status == "C":
            color = "green"
            message = "Completed"
        elif instance.status == "S":
            color = "yellow"
            message = "Started"
        else:
            color = "grey"
            message = "?"
        return mark_safe('<span style="color:%s">%s</span>' % (color, message))

    list_display = ["started", "ended", "get_status", "source_file"]

    def get_queryset(self, request):
        return pharmacy_models.ImportHistory.objects.all()

    def get_form(self, request, obj=None, **kwargs):
        if not obj:
            kwargs["form"] = forms.CompoundImportHistoryForm
        return super(CompoundImportAdmin, self).get_form(request, obj, **kwargs)

    def change_form_title(self, object_id):
        return str(pharmacy_models.ImportHistory._default_manager.get(pk=object_id))


admin.site.register(CompoundImport, CompoundImportAdmin)


class TakingFrequencyAdmin(KIOLAAdmin):
    list_display = ["name", "description"]


admin.site.register(models.TakingFrequency, TakingFrequencyAdmin)


class MedicationTypeAdmin(KIOLAAdmin):
    list_display = ["name", "description"]


admin.site.register(models.MedicationType, MedicationTypeAdmin)


class TCCPrescriptionAdmin(KIOLAAdmin):
    list_display = (
        "subject",
        "compound",
        "displayable_taking",
        "status",
        "medication_type",
    )


admin.site.register(models.TCCPrescription, TCCPrescriptionAdmin)
