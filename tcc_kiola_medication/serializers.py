from rest_framework import serializers
import json
# from .models import MedCompound
from kiola.kiola_med.models import *
from kiola.kiola_med import models as med_models
from . import models

class CompoundaSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Compound
        fields = ['pk','name','dosage_form']

class CompoundSerializer(serializers.ModelSerializer):

    activeComponents = serializers.CharField(source='active_components_name')
    source = serializers.CharField(source='source.__str__')

    class Meta:
        model =  Compound
        fields = ['pk', 'uid','name', 'source','indications','activeComponents','dosage_form','dosage_form_ref']

class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Prescription
        fields = ['taking_reason','taking_hint','displayable_taking','compound_id','subject_id']

class PatientAdverseReactionSerializer(serializers.ModelSerializer):
    reactionType = serializers.CharField(source='reaction_type.name')
    
    class Meta:
        model =  models.PatientAdverseReaction
        fields = ['pk', 'uid','substance','reactionType', 'reactions', 'created', 'updated', 'active']

class MedicationAdverseReactionSerializer(serializers.ModelSerializer):
    reactionType = serializers.CharField(source='reaction_type.name')
    compoundName = serializers.CharField(source='compound.name')
    compoundId = serializers.CharField(source='compound.pk')
    editor = serializers.CharField(source='editor.username')
    
    class Meta:
        model =  models.MedicationAdverseReaction
        fields = ['pk', 'uid', 'compoundId', "compoundName", 'reactionType', 'reactions', 'editor', 'created', 'updated', 'active']

class MedPrescriptionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='pk')
    compoundName = serializers.CharField(source='compound.name')
    compoundId = serializers.CharField(source='compound.pk')
    dosage_form = serializers.CharField(source='compound.dosage_form')
    activeComponents = serializers.SerializerMethodField()
    medicationAdverseReactions = serializers.SerializerMethodField()
    schedules = serializers.SerializerMethodField()
    prescrEvent = serializers.SerializerMethodField()

    def get_medicationAdverseReactions(self, obj):
        try:
            return obj.adverse_reactions
        except:
            return None

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

    def get_prescrEvent(self, obj):
        start = obj.prescriptionevent_set.filter(etype=med_models.PrescriptionEventType.objects.get(name=const.EVENT_TYPE__PRESCRIBED)).first()
        end = obj.prescriptionevent_set.filter(etype=med_models.PrescriptionEventType.objects.get(name=const.EVENT_TYPE__END)).first()

        return {
            'start': start.timepoint if start else None,
            'end': end.timepoint if end else None
        }

    class Meta:
        model =  Prescription
        fields = [
                    'id',
                    'taking_reason',
                    'taking_hint',
                    'displayable_taking',
                    'compoundId',
                    'compoundName',
                    'dosage_form',
                    'activeComponents',
                    'medicationAdverseReactions',
                    'schedules',
                    'prescrEvent',
                 ]


class ScheduledTakingSerializer(serializers.ModelSerializer):
    medicationId = serializers.CharField(source='prescr_id')
    frequency = serializers.CharField(source='frequency.name')
    formulation = serializers.CharField(source='unit.name')
    schedule = serializers.SerializerMethodField()
    startTime = serializers.CharField(source='start_date')
    def get_schedule(self, obj):
        if obj.timepoint.name == "custom":
            return {
              'type': obj.timepoint.name,
              'time': obj.taking_time
            }
        else:

            return {
              'type': 'solar',
              'time': obj.timepoint.name,
              'actual': obj.taking_time
            }

    class Meta:
        model =  models.ScheduledTaking
        fields = [
            "id",
            "medicationId",
            "startTime",
            "strength",
            "dosage",
            "formulation",
            "frequency",
            "reminder",
            "clinic_scheduled",
            'schedule',
        ]