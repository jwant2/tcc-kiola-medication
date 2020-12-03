from rest_framework import serializers
import json
# from .models import MedCompound
from kiola.kiola_med.models import *
from kiola.kiola_med import models as med_models, const as med_const
from kiola.kiola_senses import models as sense_models
from kiola.cares import models as cares_models
from . import models, const

class CompoundaSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='pk')

    class Meta:
        model =  med_models.Compound
        fields = ['id','name','dosage_form']

class CompoundSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='uid')
    activeComponents = serializers.SerializerMethodField()
    source = serializers.CharField(source='source.__str__')
    formulation = serializers.CharField(source='dosage_form')

    class Meta:
        model =  med_models.Compound
        fields = ['id','name', 'source','activeComponents','formulation']

    def get_activeComponents(self, obj):
        return obj.active_components.all().values_list('name', flat=True)

class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model =  med_models.Prescription
        fields = ['taking_reason','taking_hint','displayable_taking','compound_id','subject_id']

class PatientAdverseReactionSerializer(serializers.ModelSerializer):
    reactionType = serializers.CharField(source='reaction_type.name')
    
    class Meta:
        model =  models.PatientAdverseReaction
        fields = ['uid','substance','reactionType', 'reactions', 'created', 'updated', 'active']

class MedicationAdverseReactionSerializer(serializers.ModelSerializer):
    reactionType = serializers.CharField(source='reaction_type.name')
    compound = serializers.SerializerMethodField()
    createdAt = serializers.CharField(source='created')
    updatedAt = serializers.CharField(source='updated')

    class Meta:
        model =  models.MedicationAdverseReaction
        fields = ['uid', 'compound', 'reactionType', 'reactions', 'createdAt', 'updatedAt', 'active']

    def get_compound(self, obj):
        return {
            'id': obj.compound.uid,
            'name': obj.compound.name,
        }


class MedPrescriptionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='pk')
    compound = serializers.SerializerMethodField()
    formulation = serializers.CharField(source='compound.dosage_form')
    reason = serializers.CharField(source='taking_reason')
    hint = serializers.CharField(source='taking_hint')
    schedules = serializers.SerializerMethodField()
    medicationType = serializers.SerializerMethodField()
    startDate = serializers.SerializerMethodField()
    endDate = serializers.SerializerMethodField()

    def get_compound(self, obj):
        return {
            'id': obj.compound.uid,
            'name': obj.compound.name,
            'activeComponents': obj.compound.active_components.all().values_list('name', flat=True)
        }

    def get_medicationType(self, obj):
        extra_info = models.PrescriptionExtraInformation.objects\
          .filter(prescription__pk=obj.pk, name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE)\
          .order_by('pk')\
          .last()
        if not extra_info:
            extra_info = models.CompoundExtraInformation.objects\
                .filter(compound=obj.compound, name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE)\
                .order_by('pk')\
                .last()
            if extra_info:
                return extra_info.value
            else:
                return None
        else:
            return extra_info.value


    def get_medicationAdverseReactions(self, obj):
        seperator = ","
        reactions = models.MedicationAdverseReaction.objects.filter(
                        compound=obj.compound,
                        active=True,
                        editor=obj.subject.login
                    ).values_list('reactions', flat=True)
        value = seperator.join(reactions)
        return value

    def get_activeComponents(self, obj):
        return obj.compound.active_components.all().values_list('name', flat=True)

    def get_schedules(self, obj):

        takings_ids = obj.prescriptionschema_set.all().values_list('taking_schema__takings__pk', flat=True)
        takings = models.ScheduledTaking.objects.filter(pk__in=takings_ids)
        processed = []
        for taking in takings:
            processed.append({
              "id": taking.pk,
              "display": force_text(taking)
              })
        return processed

    def get_startDate(self, obj):
        pre_evt = obj.prescriptionevent_set.filter(etype=med_models.PrescriptionEventType.objects.get(name=med_const.EVENT_TYPE__PRESCRIBED)).first()
        return pre_evt.timepoint if pre_evt else None

    def get_endDate(self, obj):
        pre_evt = obj.prescriptionevent_set.filter(etype=med_models.PrescriptionEventType.objects.get(name=med_const.EVENT_TYPE__END)).first()
        return pre_evt.timepoint if pre_evt else None


    class Meta:
        model =  Prescription
        fields = [
                    'id',
                    'reason',
                    'hint',
                    'compound',
                    'formulation',
                    'schedules',
                    'startDate',
                    'endDate',
                    'medicationType'
                 ]


class ScheduledTakingSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='pk')
    medicationId = serializers.CharField(source='prescr_id')
    frequency = serializers.CharField(source='frequency.name')
    formulation = serializers.CharField(source='unit.name')
    startDate = serializers.CharField(source='start_date')
    endDate = serializers.CharField(source='end_date')
    modality = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    actualTime = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    def get_type(self, obj):
        if obj.timepoint.name == "custom":
            return obj.timepoint.name 
        else:
            return "solar"

    def get_time(self, obj):
        if obj.timepoint.name == "custom":
            return obj.taking_time
        else:
            return obj.timepoint.name

    def get_actualTime(self, obj):
        if obj.timepoint.name == "custom":
            return None
        else:
            return obj.taking_time

    def get_modality(self, obj):
        if sense_models.Subject.objects.filter(login=obj.editor).count() > 0:
            return "patient"
        elif obj.editor.pk != 1: # check if system user
            return "clinician"
        else:
            return "automate"

    class Meta:
        model =  models.ScheduledTaking
        fields = [
            "id",
            "medicationId",
            "startDate",
            "endDate",
            "strength",
            "dosage",
            "formulation",
            "frequency",
            "reminder",
            "modality",
            'hint',
            'time',
            'type',
            'actualTime',
        ]