from rest_framework import serializers

# from .models import MedCompound
from kiola.kiola_med.models import *
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