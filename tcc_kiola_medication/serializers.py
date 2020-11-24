from rest_framework import serializers
import json
# from .models import MedCompound
from kiola.kiola_med.models import *
from kiola.kiola_med import models as med_models
from . import models
# class MedCompoundSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = MedCompound
#         fields = ['pk','name','dosage_form']

class CompoundaSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Compound
        fields = ['pk','name','dosage_form']

class CompoundSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Compound
        fields = ['uid','name', 'source','indications','active_components','dosage_form','dosage_form_ref']

    # source = models.ForeignKey(CompoundSource)
    # uid = models.CharField(max_length=100)
    # name = models.CharField(max_length=255)
    # active_components = models.ManyToManyField(ActiveComponent)
    # indications = models.ManyToManyField(Indication)
    # dosage_form = models.CharField(max_length=255, null=True)
    # dosage_form_ref = models.CharField(max_length=10, null=True)

class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Prescription
        fields = ['taking_reason','taking_hint','displayable_taking','compound_id','subject_id']

# class MedCompoundSerializerTest(serializers.Serializer):
#     name = serializers.CharField(read_only=True)
#     def create(self, validated_data):

#         return MedCompound.objects.create(**validated_data)

    # def update(self, instance, validated_data):
    #     """
    #     Update and return an existing `Snippet` instance, given the validated data.
    #     """
    #     instance.title = validated_data.get('title', instance.title)
    #     instance.code = validated_data.get('code', instance.code)
    #     instance.linenos = validated_data.get('linenos', instance.linenos)
    #     instance.language = validated_data.get('language', instance.language)
    #     instance.style = validated_data.get('style', instance.style)
    #     instance.save()
    #     return instance

class PatientAdverseReactionSerializer(serializers.ModelSerializer):
    reaction_type_name = serializers.CharField(source='reaction_type.name')
    
    class Meta:
        model =  models.PatientAdverseReaction
        fields = ['uid','substance','reaction_type_name', 'reactions', 'created', 'updated']

class MedicationAdverseReactionSerializer(serializers.ModelSerializer):
    reactionType = serializers.CharField(source='reaction_type.name')
    compoundId = serializers.CharField(source='compound.name')
    editor = serializers.CharField(source='editor.username')
    
    class Meta:
        model =  models.MedicationAdverseReaction
        fields = ['uid', 'compound', "compoundId", 'reactionType', 'reactions', 'editor', 'created', 'updated', 'active']

class MedPrescriptionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='pk')
    compoundName = serializers.CharField(source='compound.name')
    medicationId = serializers.CharField(source='compound.pk')
    dosage_form = serializers.CharField(source='compound.dosage_form')
    activeComponents = serializers.SerializerMethodField()
    adverse_reactions = serializers.SerializerMethodField()
    schedules = serializers.SerializerMethodField()
    prescrEvent = serializers.SerializerMethodField()

    def get_adverse_reactions(self, obj):
        try:
            return obj.adverse_reactions
        except:
            return None

    def get_activeComponents(self, obj):
        return obj.compound.active_components.all().values_list('name', flat=True)

    def get_schedules(self, obj):
        # takings = obj.prescriptionschema_set.all().values_list('taking_schema__serialized_takings', flat=True)
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
                    'medicationId',
                    'compoundName',
                    'dosage_form',
                    'activeComponents',
                    'adverse_reactions',
                    'schedules',
                    'prescrEvent',
                 ]


class ScheduledTakingSerializer(serializers.ModelSerializer):
    medicationId = serializers.CharField(source='prescr_id')
    # medicationId = serializers.SerializerMethodField()
    frequency = serializers.CharField(source='frequency.name')
    unit = serializers.CharField(source='unit.name')
    schedule = serializers.SerializerMethodField()

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

    # def get_medicationId(self, obj):
        # taking = obj.annotate
 
    # def get_taking_time_value(self, obj):
    #     if obj.timepoint.name == "custom":
    #         return obj.taking_time
    #     else:
    #         return obj.timepoint.name

    # def get_frequency_name(self, obj):
    #     return obj.frequency.name

    # def get_unit_name(self, obj):
    #     return obj.unit.name

    class Meta:
        model =  models.ScheduledTaking
        fields = [
            "id",
            "medicationId",
            "start_date",
            "strength",
            "dosage",
            "unit",
            "frequency",
            "reminder",
            "clinic_scheduled",
            'schedule',
        ]