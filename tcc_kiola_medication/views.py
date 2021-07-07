from functools import reduce
import operator
from datetime import datetime
import csv, io
import uuid
import dateutil.parser
import shortuuid
from jsonschema import validate
from itertools import chain

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic    
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, get_language
from django.template import loader
from django import http
from django.template.loader import get_template
from django.conf import settings
from django.utils.encoding import force_text
from django.db import transaction
from django.contrib import messages
from django.core import serializers
from django.db.models import Q, Prefetch, Subquery, OuterRef, F
from django.template.response import TemplateResponse
from django.contrib.contenttypes.models import ContentType

from reversion import models as reversion
from reversion import revisions as reversionrevisions
from reversion import models as re_models

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, generics, mixins, status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework import serializers as drf_serializers
from rest_framework.authentication import SessionAuthentication, BaseAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import JSONRenderer
# import rest_framework.pagination #? FIXME:

from diplomat.models import ISOLanguage, ISOCountry
from drf_yasg.utils import swagger_auto_schema, swagger_serializer_method
from drf_yasg import openapi
#from .models import MedCompound

from kiola.kiola_pharmacy import models as pharmacy_models
from kiola.utils import authentication
from kiola.utils.drf import KiolaAuthentication
from kiola.utils.decorators.api import requires, returns
from kiola.utils.commons import http_client_codes
from kiola.utils import const as kiola_const
from kiola.utils.authentication import requires_api_login
from kiola.kiola_senses import resource
from kiola.utils import views as kiola_views
from kiola.kiola_senses import models as senses
from kiola.utils.commons import get_system_user
from kiola.utils import service_providers
from kiola.kiola_med import models as med_models
from kiola.kiola_med import views as med_views
from kiola.kiola_med import const as med_const
from kiola.kiola_med import utils as med_utils
from kiola.utils import exceptions
import kiola.utils.forms as utils_forms
from kiola.kiola_configuration import models as configuration
from kiola.kiola_configuration import utils as configuration_utils

from . import models, const, utils, docs, forms
from . import serializers as tcc_serializers
from .utils import PaginationHandlerMixin, set_default_user_pref_med_time_values
from .schema import request_body_schema as request_schema

get_for_model = ContentType.objects.get_for_model


class BasicPagination(PageNumberPagination):
    page_size_query_param = 'limit'

class CompoundAPIView(APIView, PaginationHandlerMixin):
    max_count = 80
    pagination_class = BasicPagination
    serializer_class = tcc_serializers.CompoundSerializer
    authentication_classes = [KiolaAuthentication,]

    @swagger_auto_schema(
        tags=['Compound'], 
        operation_description="GET /prescription/compound/",
        operation_summary="Query Compound resources",
        responses={
            '200':docs.compound_res,
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def get(self, request, subject_uid=None, id=None, default=None, *args, **kwargs):
        
        template = med_models.Compound.objects.select_related('source')
        if id:
            qs = template.filter(uid=id)
            if qs.count() > 0:
                serializer = self.serializer_class(qs.last())
            else:
                raise exceptions.BadRequest("Given compound id '%s' does not exists " % id)
        elif default is not None:
            query = request.GET
            request.query_params._mutable = True
            request.query_params['limit'] = self.max_count
            request.query_params._mutable = False
            default_meds_config = configuration_utils.get_configuration_for_category(
                const.TCC_MEDS_CONFIGURATION_CATEGORY
            ).get(const.TCC_MEDS_DEFAULT_MEDICINE_LIST)
            qs = template.filter(name__in=default_meds_config).order_by('name')
            qs = qs.filter(Q(source__default=True)|Q(source__version=const.COMPOUND_SOURCE_VERSION__PATIENT))
            page = self.paginate_queryset(qs)
            if page is not None:
                serializer = self.get_paginated_response(self.serializer_class(page,
                                                          many=True).data)
            else:
                serializer = self.serializer_class(qs, many=True)
        else:
            query = request.GET

            # set default value to limit param if not exist
            # to ensure paging is enabled
            if query.get('limit', None) is None:
                request.query_params._mutable = True
                request.query_params['limit'] = self.max_count
                request.query_params._mutable = False

            compound_name=query.get('compound', None)
            active_component=query.get('active_components', None)


            if compound_name:
                # if len(compound_name) < 3:
                #     msg = {'message': "Please enter at least 3 characters for better search results."}
                #     return Response(msg, status=status.HTTP_200_OK)
                qs = template.filter(name__icontains=compound_name)

            elif active_component:
                # if len(active_component) < 3:
                #     msg = {'message': "Please enter at least 3 characters for better search results."}
                #     return Response(msg, status=status.HTTP_200_OK)
                qs = template.filter(active_components__name__icontains=active_component)

            else:
                 qs = template.all()

            # if qs.count() > self.max_count and (compound_name or compound_name):
            #     msg = {'message': "More than %(max)s results found (%(amount)s). Please refine your search.." % {'max': self.max_count, 'amount': qs.count()}}
            #     return Response(msg, status=status.HTTP_200_OK)

            qs = qs.filter(Q(source__default=True)|Q(source__version=const.COMPOUND_SOURCE_VERSION__PATIENT))
            # attemp to put the default med list at front
            default_meds_config = configuration_utils.get_configuration_for_category(const.TCC_MEDS_CONFIGURATION_CATEGORY).get(const.TCC_MEDS_DEFAULT_MEDICINE_LIST)
            default_list = qs.filter(name__in=default_meds_config).order_by('name')
            rest_list = qs.exclude(id__in=default_list.values_list('id', flat=True)).order_by('name')
            qs = list(chain(default_list, rest_list))
            page = self.paginate_queryset(qs)

            if page is not None:
                serializer = self.get_paginated_response(self.serializer_class(page,
                                                          many=True).data)

            else:
                serializer = self.serializer_class(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=['Compound'], 
        operation_description="POST /prescription/compound/",
        operation_summary="Create Compound resources",
        responses={
            '200':docs.compound_res,
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def post(self, request, subject_uid=None, id=None, *args, **kwargs):
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        data = request.data
        try:
            validate(instance=data, schema=request_schema.CreateCompoundBody)
        except Exception as err: 
            msg = err
            if hasattr(err, 'message'):
                msg = err.message
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields. Error: '%s' " % (request.data, msg))

        active_omponents = data["activeComponents"]
        compound_name = data['name']
        formulation = data['formulation']
        med_type = data['medicationType']
        seperator = ","
        active_omponents = seperator.join(active_omponents)
        exist = med_models.Compound.objects.filter(name=compound_name).count()
        if exist > 0:
            raise exceptions.BadRequest("Given compound name '%s' already exists " % compound_name)

        # get patient compound source
        source = med_models.CompoundSource.objects.get(name=const.COMPOUND_SOURCE_NAME__TCC,
                                  version=const.COMPOUND_SOURCE_VERSION__PATIENT)
        current_num = med_models.Compound.objects.filter(source=source).count()
        uid = f'{const.PATIENT_ENTERED_COMPOUND_UID_PREFIX}-{current_num+1}'
        dosageform=formulation
        dosageform_ref = dosageform[:3].upper()
        if dosageform == "":
            dosageform = "N/A"
            dosageform_ref = "N/A"



        with reversionrevisions.create_revision():
            reversionrevisions.set_user(get_system_user())

            unit, created = med_models.TakingUnit.objects.get_or_create(name=dosageform)
            if created:
                unit.descrition=dosageform_ref
                unit.save

            # create active components
            ac,  created = med_models.ActiveComponent.objects.get_or_create(name=active_omponents)
            if created:
                ac.name_ref = uid
                ac.save()

            # create or update compound data
            compound, created = med_models.Compound.objects.get_or_create(
                uid=uid,
                name=compound_name,
                source=source,
                dosage_form=dosageform,
                dosage_form_ref=dosageform_ref,
                registration_number=request.user.username,
              )
            active_components = compound.active_components.all()
            compound.active_components.add(ac)
            compound.save()

        prn, created = models.CompoundExtraInformation.objects.get_or_create(compound=compound, name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE)
        if created:
            prn.value = med_type
            prn.save()

        serializer = tcc_serializers.CompoundSerializer(compound)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MedObservationProfileAPIView(APIView):

    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]

    @swagger_auto_schema(
        tags=['MedicationObservationProfile'], 
        operation_description="GET /prescription/med_obs_profiles/",
        operation_summary="Query Medication observation profiles",
        responses={
            '200': openapi.Schema(
                  type=openapi.TYPE_ARRAY,
                  items=openapi.Schema(
                      type=openapi.TYPE_OBJECT,
                          properties={
                              "id": openapi.Schema(type=openapi.TYPE_NUMBER, description='Root observation profile Id'),

                              "children": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_NUMBER, description='Prescription related observation profile Id'),
                                        },
                                        description='Prescription related observation profile'),
                                    description='Prescription related observation profiles'),

                          }
                  ),
                  description='Root observation profiles'
              ),
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def get(self, request, subject_uid=None,uid=None, *args, **kwargs):
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        active_ppr = med_models.PrescriptionProfileRelation.objects.filter(active=True, root_profile__subject=subject).first()
        if active_ppr:
            root_profile = active_ppr.root_profile
            data = [
                    {"id": root_profile.name}
                ]
            
            children = root_profile.children.all()
            if len(children) > 0:
                data[0]['children'] = []
                for child in children:

                    data[0]['children'].append({
                        "id": child.name
                    })
        else:
            data = []

        return Response(data, status=status.HTTP_200_OK)




class PrescriptionAPIView(APIView, PaginationHandlerMixin):
    max_count = 80
    pagination_class = BasicPagination
    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]
    serializer_class = tcc_serializers.MedPrescriptionSerializer

    @swagger_auto_schema(
        tags=['Medication'], 
        operation_description="GET /prescription/medication/",
        operation_summary="Query medication",
        responses={
            '200': docs.prescr_res,
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def get(self, request, subject_uid=None, id=None, *args, **kwargs):

        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        prescr_id = id
        if prescr_id:
            try:
                prescr = models.TCCPrescription.objects.select_related(
                'compound',
                'status') .filter(
                pk=prescr_id,
                subject=subject,
                status__name=med_const.PRESCRIPTION_STATUS__ACTIVE) .prefetch_related(
                Prefetch(
                    'prescriptionevent_set',
                    queryset=med_models.PrescriptionEvent.objects.filter(
                        etype__name__in=[
                            med_const.EVENT_TYPE__PRESCRIBED,
                            med_const.EVENT_TYPE__END,
                        ]) .select_related("etype") .order_by("timepoint")),
                Prefetch(
                    'prescriptionevent_set',
                    queryset=med_models.PrescriptionEvent.objects.filter(
                        etype__name__in=[
                            med_const.EVENT_TYPE__ADDED,
                        ]) .select_related("etype") .order_by("timepoint"),
                    to_attr="added_on"),
                'compound__indications',
                'compound__active_components') .order_by(
                'compound__name',
                'status')[0]


            except:
                raise exceptions.BadRequest("Prescription with id '%s' does not exist or is inactive" % prescr_id)
            serializer = self.serializer_class(prescr)

        else:
            query = request.GET

            # set default value to limit param if not exist
            # to ensure paging is enabled
            if query.get('limit', None) is None:
                request.query_params._mutable = True
                request.query_params['limit'] = self.max_count
                request.query_params._mutable = False

            active = query.get('active', None)
            if active:
                  if active not in ['True', 'False', 'true', 'false']:
                      raise exceptions.BadRequest("Invalid data '%s' for active. Should be 'true' or 'false'." % active)
                  active = active.lower()
            qs = models.TCCPrescription.objects.select_related(
                'compound',
                'status').filter(subject=subject).prefetch_related(
                Prefetch(
                    'prescriptionevent_set',
                    queryset=med_models.PrescriptionEvent.objects.filter(
                        etype__name__in=[
                            med_const.EVENT_TYPE__PRESCRIBED,
                            med_const.EVENT_TYPE__END,
                        ]) .select_related("etype") .order_by("timepoint")),
                Prefetch(
                    'prescriptionevent_set',
                    queryset=med_models.PrescriptionEvent.objects.filter(
                        etype__name__in=[
                            med_const.EVENT_TYPE__ADDED,
                        ]) .select_related("etype") .order_by("timepoint"),
                    to_attr="added_on"),
                'compound__indications',
                'compound__active_components') .order_by(
                'compound__name',
                'status')
            if active == "true":
                  qs = qs.filter(status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
            if active == "false":
                  qs = qs.filter(status__name=med_const.PRESCRIPTION_STATUS__INACTIVE)
            page = self.paginate_queryset(qs)

            if page is not None:
                serializer = self.get_paginated_response(self.serializer_class(page,
                                                          many=True).data)

            else:
                serializer = self.serializer_class(qs, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @requires_api_login
    def delete(self, request, subject_uid=None, id=None, *args, **kwargs):  
        prescr_id = id
        if not prescr_id:
            raise exceptions.BadRequest("Invalid request. Missing resource id")

        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        try:
            prescription = models.TCCPrescription.objects.get(subject=subject, pk=prescr_id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
        except models.TCCPrescription.DoesNotExist:
            raise exceptions.NotFound("Prescription with id '%s' does not exist or is inactive" % prescr_id)

        p_status = med_models.PrescriptionStatus.objects.get(name=med_const.PRESCRIPTION_STATUS__INACTIVE)

        with transaction.atomic():

            with reversionrevisions.create_revision():
                reversionrevisions.set_user(get_system_user())
            med_models.PrescriptionEvent.objects.create(prescription=prescription,
                                                    timepoint=timezone.now(),
                                                    etype=med_models.PrescriptionEventType.objects.get(name=med_const.EVENT_TYPE__CANCELED))
            prescription.status = p_status
            prescription.save()

        return Response({"id": prescr_id}, status=status.HTTP_200_OK)

    @requires_api_login
    def put(self, request, subject_uid=None, id=None, *args, **kwargs):  
        prescr_id = id
        if not prescr_id:
            raise exceptions.BadRequest("Invalid request. Missing resource id")
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        try:
            validate(instance=request.data, schema=request_schema.CreateMedicationBody)
        except Exception as err: 
            msg = err
            if hasattr(err, 'message'):
                msg = err.message
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields. Error: '%s' " % (request.data, msg))
        prescr = self._create_or_update(request, prescr_id, subject)
        # prepare object for response
        prescr = models.TCCPrescription.objects.get(pk=prescr.pk)
        serializer = self.serializer_class(prescr)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=['Medication'], 
        operation_description="POST /prescription/medication/",
        operation_summary="Create/update medication",
        request_body=docs.prescr_req,
        responses={
            '200': docs.prescr_res,
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def post(self, request, subject_uid=None, id=None, *args, **kwargs):  
        if id is not None:
            raise exceptions.BadRequest("Creating new resource with given id is not supported.")
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        try:
            validate(instance=request.data, schema=request_schema.CreateMedicationBody)
        except Exception as err: 
            msg = err
            if hasattr(err, 'message'):
                msg = err.message
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields. Error: '%s' " % (request.data, msg))

        prescr_id = id
        prescr = self._create_or_update(request, prescr_id, subject)
        # prepare object for response
        prescr = models.TCCPrescription.objects.get(pk=prescr.pk)
        serializer = self.serializer_class(prescr)

        return Response(serializer.data, status=status.HTTP_200_OK)


    def _create_or_update(self, request, prescr_id, subject): 
        # filter extra fields that are not allowed for storing history records
        def process_request_data(request_data):
            data = {
              'compound': request_data.get('compound', None),
              'reason': request_data.get('reason', ""),
              'hint': request_data.get('hint', ""),
              'dosage': request_data.get('medicationDosage', ""),
              'unit': request_data.get('formulation', ""),
              'strength': request_data.get('strength', ""),
              'medicationAdverseReactions': request_data.get("medicationAdverseReactions", ""),
              'medicationType': request_data.get('medicationType', None),
              'startDate': request_data.get('startDate', None),
              'endDate': request_data.get('endDate', None),    
              'active': request_data.get('active', None),    
            }
            return data

        processed_data = process_request_data(request.data) ## filter unnessary data fields
        processed_data['id'] = str(prescr_id) if prescr_id else None
        compound_obj = processed_data.get('compound', None)
        if not compound_obj or not compound_obj.get('id', None):
            raise exceptions.BadRequest("Invalid data. Missing compound id")
        taking_reason = processed_data.get('reason', "")
        taking_hint = processed_data.get('hint', "")
        dosage = processed_data.get('dosage', "")
        strength = processed_data.get('strength', "")
        active = processed_data.get('active', None)  
        unit_value = processed_data.get('unit', None)
        medication_type = processed_data.get('medicationType', None)
        p_start = processed_data.get('startDate', None)
        p_end = processed_data.get('endDate', None)

        start_date = None
        if p_start:
            start_date = datetime.strptime(p_start.split("T")[0], "%Y-%m-%d").astimezone(timezone.utc)
        else:
            # set prescrition_start as now() if it is missing
            start_date = datetime.now().astimezone(timezone.utc)
        end_date = None
        if p_end:
            end_date = datetime.strptime(p_end.split("T")[0], "%Y-%m-%d").astimezone(timezone.utc)

        if medication_type and medication_type not in const.MEDICATION_TYPE_VALUES:
            raise exceptions.BadRequest("Invalid data '%s' for medicationType" % medication_type)
        elif not medication_type:
            raise exceptions.BadRequest("Invalid data '%s' for medicationType" % medication_type)

        if not unit_value:
            raise exceptions.BadRequest("Invalid data '%s' for unit" % unit)
        unit, _ = med_models.TakingUnit.objects.get_or_create(name=unit_value)
        
        if active is not None and type(active) != bool:
            raise exceptions.BadRequest("Invalid data '%s' " % processed_data)
        if prescr_id:
            try:
                prescr = models.TCCPrescription.objects.get(pk=prescr_id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
                
            except:
                raise exceptions.BadRequest("Prescription with id '%s' does not exist or is inactive" % prescr_id)

            if prescr.compound.uid != compound_obj['id']:
                raise exceptions.BadRequest("Compound with id '%s' does not match the compound of the given prescription with id '%s'" % (compound_obj['id'], prescr_id))

            with reversionrevisions.create_revision():
                reversionrevisions.set_user(get_system_user())

            med_type = models.MedicationType.objects.get(name=medication_type)

            start = prescr.prescriptionevent_set.filter(etype=med_models.PrescriptionEventType.objects.get(name=med_const.EVENT_TYPE__PRESCRIBED))[0]
            start.timepoint = start_date
            start.save()
            end = prescr.prescriptionevent_set.filter(etype=med_models.PrescriptionEventType.objects.get(name=med_const.EVENT_TYPE__END))
            if len(end) > 0 and end_date:
                end[0].timepoint =end_date
                end[0].save()

            prescr.taking_hint = taking_hint
            prescr.taking_reason =  taking_reason
            prescr.dosage = dosage
            prescr.strength =  strength
            prescr.unit =  unit
            prescr.medication_type = med_type
            if active is not None and active is False:
                prescr_stauts_inactive = med_models.PrescriptionStatus.objects.get(name=med_const.PRESCRIPTION_STATUS__INACTIVE)
                prescr.status = prescr_stauts_inactive
            prescr.save()

        else:
            p_status = med_models.PrescriptionStatus.objects.get(name="Active")
            with reversionrevisions.create_revision():
                reversionrevisions.set_user(get_system_user())
                try:
                    adapter = med_models.Compound.objects.get_adapter(med_models.CompoundSource.objects.get(default=True).pk)
                    compound, created = adapter.get_or_create(compound_obj['id'])
                except: 
                    # check if patient created compound
                    try:
                        source = med_models.CompoundSource.objects.get(name=const.COMPOUND_SOURCE_NAME__TCC,
                                              version=const.COMPOUND_SOURCE_VERSION__PATIENT)
                        compound = med_models.Compound.objects.get(uid=compound_obj['id'], source=source)
                    except:
                        raise exceptions.BadRequest("Compound with id '%s' does not exist" % compound_obj['id'])         

                if not compound:
                    raise exceptions.BadRequest("Compound with id '%s' does not exist" % compound_obj['id'])

                med_type = models.MedicationType.objects.get(name=medication_type)
                prescr, replaced = models.TCCPrescription.objects.prescribe(subject=subject,
                                                                          prescriber=request.user,
                                                                          compound=compound,
                                                                          reason=taking_reason,
                                                                          hint=taking_hint,
                                                                          start=start_date,
                                                                          dosage=dosage,
                                                                          strength=strength,
                                                                          unit=unit,
                                                                          med_type=med_type,
                                                                          end=end_date)
            

        # save change history
        if processed_data.get('id', None) is None:
            processed_data['id'] = str(prescr.pk)
        record = models.MedicationRelatedHistoryData.objects.add_data_change_record(prescr, processed_data)

        return prescr

def update_or_create_med_adverse_reaction(request, reactions_str: str, compound: med_models.Compound):
    reactions = reactions_str.split(',')
    reaction_type = models.AdverseReactionType.objects.get(name=const.ADVERSE_REACTION_TYPE__UNKNOWN)
    for item in reactions:
        exist = models.MedicationAdverseReaction.objects.filter(compound=compound, reactions=reactions, editor=request.user).count()
        if exist == 0 and item != "":
            reaction_item, created = models.MedicationAdverseReaction.objects.get_or_create(
                compound=compound, reaction_type=reaction_type, reactions=item, editor=request.user)

def update_prescription_displayable_taking(prescription):
    takings = models.ScheduledTaking.objects.filter(takings_set__id=prescription.id, active=True)
    taking_strings = []
    for taking in takings:
        taking_strings.append(taking.get_displayable())
    seperator = " | "
    displayable_taking = seperator.join(taking_strings)
    if len(displayable_taking) < 200:
        prescription.displayable_taking = displayable_taking
    else:
        prescription.displayable_taking = "TOO MANY TO DISPLAY"
    prescription.save()
    return displayable_taking

class PrescriptionHistoryAPIView(APIView, PaginationHandlerMixin):
    max_count = 80
    pagination_class = BasicPagination
    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]
    serializer_class = tcc_serializers.MedPrescriptionSerializer

    @swagger_auto_schema(
        tags=['Medication'], 
        operation_description="GET /prescription/medication/{id}/histroy/",
        operation_summary="Query prescription history",
        responses={
          '200': docs.prescr_history_res,
          '400': 'Bad request'
        }
    )
    @requires_api_login
    def get(self, request, subject_uid=None, id=None, *args, **kwargs):
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        try:
            prescr = models.TCCPrescription.objects.select_related('compound').get(pk=id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
        except Exception as err:
            print(err)
            raise exceptions.BadRequest("Prescription with id '%s' does not exist or is inactive" % id)

        query = request.GET

        # set default value to limit param if not exist
        # to ensure paging is enabled
        if query.get('limit', None) is None:
            request.query_params._mutable = True
            request.query_params['limit'] = self.max_count
            request.query_params._mutable = False

        qs = models.MedicationRelatedHistoryData.objects.get_history_data(prescr)

        page = self.paginate_queryset(qs)



        results = []
        for i in range(len(qs) - 1):
            A = qs[i].data
            B = qs[i+1].data 
            value = {x:(A[x], B[x]) for x in B if x in A if B[x] != A[x]}

            if value:
                temp = []
                for item in value:
                    change = value[item]
                    data = {
                        'field': item,
                        'old': change[0],
                        'new': change[1],
                    }
                    temp.append(data)
                results.append({
                    'time': force_text(qs[i+1].created),
                    'changes': temp
                })
        if page is not None:
            # queryset includes initial data record, so change history count should be -1
            self.paginator.page.paginator.count = len(results)
            return self.get_paginated_response(results)

        return Response(results, status=status.HTTP_200_OK)



class MedicationAdverseReactionAPIView(APIView, PaginationHandlerMixin):
    max_count = 80
    pagination_class = BasicPagination

    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]
    serializer_class = tcc_serializers.MedicationAdverseReactionSerializer

    @swagger_auto_schema(
        tags=['Reaction'], 
        operation_description="GET /prescription/reaction/",
        operation_summary="Query Reaction",
        responses={
            '200': docs.adverse_reaction_res,
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def get(self, request, subject_uid=None, id=None, *args, **kwargs):
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        # reaction_id = request.GET.get('id', None)
        reaction_id = id
        if reaction_id:
            try:
                reaction_item = models.MedicationAdverseReaction.objects.get(uid=reaction_id)
            except Exception as err:
                print(err)
                raise exceptions.BadRequest("MedicationAdverseReaction with id '%s' does not exist" % reaction_id)
            serializer = self.serializer_class(reaction_item)

        else:
            query = request.GET
            active = query.get('active', None)
            if active:
                  if active not in ['True', 'False', 'true', 'false']:
                      raise exceptions.BadRequest("Invalid data '%s' for active. Should be 'true' or 'false'." % active)
                  active = active.lower()
            # set default value to limit param if not exist
            # to ensure paging is enabled
            if query.get('limit', None) is None:
                request.query_params._mutable = True
                request.query_params['limit'] = self.max_count
                request.query_params._mutable = False

            qs = models.MedicationAdverseReaction.objects.filter(editor=subject.login)
            if active == "true":
                qs = qs.filter(active=True)
            if active == "false":
                qs = qs.filter(active=False)

            page = self.paginate_queryset(qs)
            if page is not None:
                serializer = self.get_paginated_response(self.serializer_class(page,
                                                          many=True).data)
            else:
                serializer = self.serializer_class(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @requires_api_login
    def delete(self, request, subject_uid=None, id=None, *args, **kwargs):  
        reaction_id = id
        if not reaction_id:
            raise exceptions.BadRequest("Invalid request. Missing resource id")

        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        try:
            reaction_item = models.MedicationAdverseReaction.objects.get(uid=reaction_id, editor=subject.login, active=True)
        except:
            raise exceptions.BadRequest("MedicationAdverseReaction with id '%s' does not exist or is inactive" % reaction_id)
        with reversionrevisions.create_revision():
            reversionrevisions.set_user(get_system_user())
            reaction_item.active = False
            reaction_item.save()

        return Response({"id": reaction_id}, status=status.HTTP_200_OK)

    @requires_api_login
    def put(self, request, subject_uid=None, id=None, *args, **kwargs):  
        reaction_id = id
        if not reaction_id:
            raise exceptions.BadRequest("Invalid request. Missing resource id")
          
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        try:
            validate(instance=request.data, schema=request_schema.CreateReactionBody)
        except Exception as err: 
            msg = err
            if hasattr(err, 'message'):
                msg = err.message
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields. Error: '%s' " % (request.data, msg))

        data = request.data
        # reaction_id = data.get('uid', None)
        compound = data.get('compound', None)
        compound_id = compound.get('id', None) if compound else None
        reaction_type_name = data.get('reactionType', None)
        reactions = data.get('reactions', None)

        reaction_item = self._create_or_update(request, reaction_id, compound_id, reaction_type_name, reactions)
        serializer = self.serializer_class(reaction_item)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=['Reaction'], 
        operation_description="POST /prescription/reaction/",
        operation_summary="Create/Update Reaction",
        request_body=docs.adverse_reaction_req,
        responses={
            '200': docs.adverse_reaction_res,
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def post(self, request, subject_uid=None, id=None, *args, **kwargs):  
        if id is not None:
            raise exceptions.BadRequest("Creating new resource with given id is not supported.")
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        try:
            validate(instance=request.data, schema=request_schema.CreateReactionBody)
        except Exception as err: 
            msg = err
            if hasattr(err, 'message'):
                msg = err.message
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields. Error: '%s' " % (request.data, msg))

        data = request.data
        # reaction_id = data.get('uid', None)
        reaction_id = id
        compound = data.get('compound', None)
        compound_id = compound.get('id', None) if compound else None
        reaction_type_name = data.get('reactionType', None)
        reactions = data.get('reactions', None)

        reaction_item = self._create_or_update(request, reaction_id, compound_id, reaction_type_name, reactions)
        serializer = self.serializer_class(reaction_item)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def _create_or_update(self, request, reaction_id, compound_id, reaction_type_name, reactions):
        if not compound_id or not reaction_type_name or not reactions:
            raise exceptions.BadRequest("Invalid data '%s' " % request.data)
                 
        try:
            reaction_type = models.AdverseReactionType.objects.get(name=reaction_type_name)
        except:
            raise exceptions.BadRequest("AdverseReactionType with name '%s' does not exist" % reaction_type_name)


        with reversionrevisions.create_revision():
            reversionrevisions.set_user(get_system_user())

        if reaction_id:
            try:
                reaction_item = models.MedicationAdverseReaction.objects.get(uid=reaction_id, editor=request.user, active=True)
            except Exception:
                raise exceptions.BadRequest("MedicationAdverseReaction with id '%s' does not exist or is inactive" % reaction_id)
            if reaction_item.compound.uid != compound_id:
                raise exceptions.BadRequest("Compound id '%s' does not match the gvien reaction (%s)" % (compound_id, reaction_id))
            
            reaction_item.reaction_type = reaction_type
            reaction_item.reactions = reactions
            reaction_item.save()

        else:
            try:
                source = med_models.CompoundSource.objects.get_default()
                adapter = med_models.Compound.objects.get_adapter(source.pk)
                compound, created = adapter.get_or_create(compound_id)
            except:
                # check if patient created compound
                try:
                    source = med_models.CompoundSource.objects.get(name=const.COMPOUND_SOURCE_NAME__TCC,
                                          version=const.COMPOUND_SOURCE_VERSION__PATIENT)
                    compound = med_models.Compound.objects.get(uid=compound_id, source=source)
                except:
                    raise exceptions.BadRequest("Compound with id '%s' does not exist" % compound_id) 

            reaction_item, created = models.MedicationAdverseReaction.objects.get_or_create(
                compound=compound, reaction_type=reaction_type, reactions=reactions, editor=request.user, active=True)
        return reaction_item

class TakingSchemaAPIView(APIView, PaginationHandlerMixin):
    max_count = 80
    pagination_class = BasicPagination

    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]
    serializer_class = tcc_serializers.ScheduledTakingSerializer

    @swagger_auto_schema(
        tags=['Schedule'], 
        operation_description="GET /prescription/schedule/",
        operation_summary="Query Schedule",
        responses={
            '200': docs.taking_res,
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def get(self, request, subject_uid=None, id=None, *args, **kwargs):

        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        # taking_id = request.GET.get('id', None)
        taking_id = id
        if taking_id:
            try:
                taking_item = models.ScheduledTaking.objects.annotate(prescr_id=
                    F('takings_set__id')
                ).get(pk=taking_id)
            except Exception as err:
                print(err)
                raise exceptions.BadRequest("ScheduledTaking with id '%s' does not exist" % taking_id)
            serializer = self.serializer_class(taking_item)

        else:
            query = request.GET
            active = query.get('active', None)
            if active:
                  if active not in ['True', 'False', 'true', 'false']:
                      raise exceptions.BadRequest("Invalid data '%s' for active. Should be 'true' or 'false'." % active)
                  active = active.lower()
            # set default value to limit param if not exist
            # to ensure paging is enabled
            if query.get('limit', None) is None:
                request.query_params._mutable = True
                request.query_params['limit'] = self.max_count
                request.query_params._mutable = False
            start_date = query.get('startDate', None)
            end_date = query.get('endDate', None)
            given_date = query.get('date', None)

            taking_qs = (
                models.ScheduledTaking.objects.filter(
                    takings_set__subject=subject,
                    takings_set__status__name=med_const.PRESCRIPTION_STATUS__ACTIVE,
                )
                .annotate(prescr_id=
                    F('takings_set__id')
                )
            )
            if start_date:
                try:
                    start = dateutil.parser.parse(start_date)
                except:
                    raise exceptions.BadRequest("Invalid datetime format '%s' for startDate. " % start_date)
                taking_qs = taking_qs.filter(start_date__gte=start)
            if end_date:
                try:
                    end = dateutil.parser.parse(end_date)
                except:
                      raise exceptions.BadRequest("Invalid datetime format '%s' for endDate. " % end_date)
                taking_qs = taking_qs.filter(Q(end_date__lte=end) | Q(end_date=None))

            if active == "true":
                taking_qs = taking_qs.filter(active=True)
            if active == "false":
                taking_qs = taking_qs.filter(active=False)

            #  start_date <= given_data <= end_date
            if given_date:
                try:
                    given = dateutil.parser.parse(given_date)
                except:
                      raise exceptions.BadRequest("Invalid datetime format '%s' for endDate. " % given_date)
                taking_qs = taking_qs.filter(Q(end_date__gte=given, start_date__lte=given) | Q(start_date__lte=given, end_date=None))
                taking_qs = utils.filter_schedule_for_given_date(given, taking_qs)

            page = self.paginate_queryset(taking_qs)
            if page is not None:
                serializer = self.get_paginated_response(self.serializer_class(page,
                                                          many=True).data)

            else:
                serializer = self.serializer_class(taking_qs, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


    @requires_api_login
    def delete(self, request, subject_uid=None, id=None, *args, **kwargs):  
        taking_id = id
        if not taking_id:
            raise exceptions.BadRequest("Invalid request. Missing resource id")
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        taking = None
        try:
            taking = models.ScheduledTaking.objects.annotate(prescr_id=F('takings_set__id')).get(pk=taking_id, active=True)
        except:
            raise exceptions.BadRequest("Taking with id '%s' does not exist or is inactive" % taking_id)

        with reversionrevisions.create_revision():
            reversionrevisions.set_user(get_system_user())
            taking.active = False
            taking.save()
        prescr = models.TCCPrescription.objects.get(pk=taking.prescr_id)
        update_prescription_displayable_taking(prescr)
        return Response({"id": taking_id}, status=status.HTTP_200_OK)


    @swagger_auto_schema(
        tags=['Schedule'], 
        operation_description="POST /prescription/schedule/",
        operation_summary="Create/Update Schedule",
        request_body=docs.taking_req,
        responses={
            '200': docs.taking_res,
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def post(self, request, subject_uid=None, id=None, *args, **kwargs):
        if id is not None:
            raise exceptions.BadRequest("Creating new resource with given id is not supported.")
        try:
            validate(instance=request.data, schema=request_schema.CreateScheduleBody)
        except Exception as err: 
            msg = err
            if hasattr(err, 'message'):
                msg = err.message
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields. Error: '%s' " % (request.data, msg))

        data = request.data
        try:
            prescr_id = data.get('medicationId', "")
            schedule_type = data['type']
            schedule_time = data['time']
            frequency = data['frequency']
            reminder = data['reminder']
            start_date = data['startDate']
            end_date = data.get('endDate', None)
            dose = data['dosage']
            strength = data['strength']
            unit = data['formulation']
            hint = data.get('hint', "")

        except: 
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields " % data)

        taking = process_taking_request(request, data, None, prescr_id, schedule_type, schedule_time, frequency, reminder, start_date, end_date, dose, strength, unit, hint)
        
        serializer = self.serializer_class(models.ScheduledTaking.objects.annotate(prescr_id=
                    F('takings_set__id')
                ).get(pk=taking.pk))

        return Response(serializer.data, status=status.HTTP_200_OK)

    @requires_api_login
    def put(self, request, subject_uid=None, id=None, *args, **kwargs):
        data = request.data

        taking_id = id
        if not taking_id:
            raise exceptions.BadRequest("Invalid request. Missing resource id")
        try:
            validate(instance=request.data, schema=request_schema.CreateScheduleBody)
        except Exception as err: 
            msg = err
            if hasattr(err, 'message'):
                msg = err.message
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields. Error: '%s' " % (request.data, msg))

        try:
            prescr_id = data.get('medicationId', "")
            schedule_type = data['type']
            schedule_time = data['time']
            frequency = data['frequency']
            reminder = data['reminder']
            start_date = data['startDate']
            end_date = data.get('endDate', None)
            dose = data['dosage']
            strength = data['strength']
            unit = data['formulation']
            hint = data.get('hint', "")

        except: 
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields " % data)

        taking = process_taking_request(request, data, taking_id, prescr_id, schedule_type, schedule_time, frequency, reminder, start_date, end_date, dose, strength, unit, hint)
        
        serializer = self.serializer_class(models.ScheduledTaking.objects.annotate(prescr_id=
                    F('takings_set__id')
                ).get(pk=taking.pk))

        return Response(serializer.data, status=status.HTTP_200_OK)

def process_taking_request(request, data, taking_id, prescr_id, schedule_type, schedule_time, frequency, reminder, start_date, end_date, dose, strength, unit, hint, clinic_scheduled=False):

        taking = None
        if taking_id:
            try:
                taking = models.ScheduledTaking.objects.get(pk=taking_id)
            except:
                raise exceptions.BadRequest("Taking with id '%s' does not exist " % taking_id)

        try:
            prescr = models.TCCPrescription.objects.get(pk=prescr_id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
        except Exception as err:
            print(err)
            raise exceptions.BadRequest("Prescription with id '%s' does not exist or is inactive" % prescr_id)
        
        if schedule_type == 'custom':
            timepoint = med_models.TakingTimepoint.objects.get(name=schedule_type.lower())
            time = datetime.strptime(schedule_time, "%H:%M")
        elif schedule_type == 'solar':
            timepoint = med_models.TakingTimepoint.objects.get(name=schedule_time.lower())
            user_pref = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user)
            if user_pref is None:
                set_default_user_pref_med_time_values(request.user)
                user_pref = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user)
            time_value = user_pref[f'{const.USER_PREFERENCE_CONFIG_PREFIX}{schedule_time}']
            time = datetime.strptime(time_value['actualTime'], "%H:%M")
        else:
            raise exceptions.BadRequest("Invalid schedule type '%s'" % schedule_type)

        
        prescr_schema = prescr.prescriptionschema_set.all().first()
        takings = prescr_schema.taking_schema.takings.all().values_list('pk', flat=True)

        should_new_takingschema = False
        with reversionrevisions.create_revision():
            reversionrevisions.set_user(get_system_user())
            for item in takings:
                try:
                    exist = models.ScheduledTaking.objects.get(pk=item)
                except:
                    should_new_takingschema = True
                    break

        taking_unit, created = med_models.TakingUnit.objects.get_or_create(name=unit)
        if taking:
            if taking.pk not in takings:
                raise exceptions.BadRequest("Taking with id '%s' does not match the gvien prescription (%s)" % (taking_id, prescr_id))


            taking.timepoint=timepoint
            taking.taking_time=time
            taking.start_date=datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
            taking.end_date=datetime.strptime(end_date.split("T")[0], "%Y-%m-%d") if end_date else None
            taking.editor=request.user
            taking.unit=taking_unit
            taking.hint=hint
            taking.strength=strength
            taking.dosage=dose
            taking.reminder=reminder
            taking.clinic_scheduled=clinic_scheduled
            taking.frequency=models.TakingFrequency.objects.get(name=frequency)
            taking.save() 

        else:
            taking = models.ScheduledTaking.objects.create(
                timepoint=timepoint,
                taking_time=time,
                end_date=datetime.strptime(end_date.split("T")[0], "%Y-%m-%d") if end_date else None,  
                start_date=datetime.strptime(start_date.split("T")[0], "%Y-%m-%d"),
                editor=request.user,
                unit=taking_unit,
                strength=strength,
                dosage=dose,
                hint=hint,
                reminder=reminder,
                clinic_scheduled=clinic_scheduled,
                frequency=models.TakingFrequency.objects.get(name=frequency)
            )
  
            if should_new_takingschema:
                schema = med_models.TakingSchema.objects.create()
                med_models.OrderedTaking.objects.create(taking=taking, schema=schema)
                schema.save()
                prescr_schema.taking_schema = schema
                prescr_schema.save()
                # for tcc prescription
                prescr.takings.add(taking)
                prescr.save()
            else:
                schema = prescr_schema.taking_schema
                ## FIXME: need to check if there is an existing taking for same prescr and timepoint?
                med_models.OrderedTaking.objects.create(taking=taking, schema=schema)
                schema.save()
                # for tcc prescription
                prescr.takings.add(taking)
                prescr.save()

        update_prescription_displayable_taking(prescr)

        return taking

class UserPreferenceConfigAPIView(APIView, PaginationHandlerMixin):
    max_count = 80
    pagination_class = BasicPagination
    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]

    @swagger_auto_schema(
        tags=['UserPreferenceConfig'], 
        operation_description="GET /prescription/user_preference_config/",
        operation_summary="Query User Preference Config resources",
        responses={
            '200': docs.user_pref_res,
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def get(self, request, *args, **kwargs):
        try:
            subject = senses.Subject.objects.get(login=request.user)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        # set default value to limit param
        # to ensure paging is enabled
        request.query_params._mutable = True
        request.query_params['limit'] = self.max_count
        request.query_params._mutable = False

        data = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user)
        if data is None: 
            set_default_user_pref_med_time_values(request.user)
            data = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user)
        config_data = data.values()

        page = self.paginate_queryset(models.UserPreferenceConfig.objects.filter(pk=1))
        if page is not None:
            self.paginator.page.paginator.count = len(config_data)
            return self.get_paginated_response(config_data)

        return Response(config_data, status=status.HTTP_200_OK) 


    # @swagger_auto_schema(
    #     tags=['UserPreferenceConfig'], 
    #     operation_description="POST /prescription/user_preference_config/",
    #     operation_summary="Create/replace UserPreferenceConfig",
    #     request_body=docs.user_pref_res,
    #     responses={
    #         '200': docs.user_pref_res,
    #         '400': "Bad Request"
    #     }
    # )
    # @requires_api_login
    # def post(self, request, *args, **kwargs):
    #     try:
    #         subject = senses.Subject.objects.get(login=request.user)
    #     except senses.Subject.DoesNotExist:
    #         raise exceptions.Forbidden("Unknown subject")
        
    #     data = request.data
    #     med_pref_data = data.get('data', None)
    #     config_data = {}
    #     for item in med_pref_data:
    #         config_data[f'{const.USER_PREFERENCE_CONFIG_PREFIX}{item["type"].lower()}'] = item
    #     result = models.UserPreferenceConfig.objects.set_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, config_data, request.user)
    #     return Response({"msg": "Success"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=['UserPreferenceConfig'], 
        operation_description="PUT /prescription/user_preference_config/",
        operation_summary="Update UserPreferenceConfig",
        request_body=docs.user_pref_res,
        responses={
            '200': "Success",
            '400': "Bad Request"
        }
    )
    @requires_api_login
    def put(self, request, *args, **kwargs):
        try:
            subject = senses.Subject.objects.get(login=request.user)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        try:
            validate(instance=request.data, schema=request_schema.UpdateUserPreferenceBody)
        except Exception as err: 
            msg = err
            if hasattr(err, 'message'):
                msg = err.message
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields. Error: '%s' " % (request.data, msg))

        med_pref_data = request.data
        config_data = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user)
        dict_check_duplicates = dict()
        processed_items = []
        for item in med_pref_data:
            # duplicate check for type value
            if item["type"] not in dict_check_duplicates:
                dict_check_duplicates[item["type"]] = item["type"]
            else:
                raise exceptions.BadRequest("Duplicate data '%s' for type" % item["type"])
            # checking time string format
            try:
                time = datetime.strptime(item["actualTime"],"%H:%M")
            except:
                raise exceptions.BadRequest("actualTime data '%s' is invalid or not in 24 hr format" % item["actualTime"])
            config_item = config_data.get(f'{const.USER_PREFERENCE_CONFIG_PREFIX}{item["type"]}', None)
            if config_item is None:
                raise exceptions.BadRequest("Invalid data for type '%s" % item['type'])
            config_data[f'{const.USER_PREFERENCE_CONFIG_PREFIX}{item["type"]}'] = item
            processed_items.append(item)

        with reversionrevisions.create_revision():
            reversionrevisions.set_user(get_system_user())
        result = models.UserPreferenceConfig.objects.set_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, config_data, request.user)
        config_data = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user).values()

        # update schedule taking
        for item in processed_items:
            time = datetime.strptime(item['actualTime'], "%H:%M")
            models.ScheduledTaking.objects.filter(Q(timepoint__name=item['type'])).update(taking_time=time)

        return Response(config_data, status=status.HTTP_200_OK)

class TCCPrescriptionListView(kiola_views.KiolaSubjectListView):
    title = _("Prescriptions")
    template_name = 'lists/prescription_list.html'
    context_object_name = 'active_prescriptions'

    @property
    def addurl_name(self):
        try:
            if med_models.CompoundSource.objects.get_default():
                return 'med:prescription_add'
        except ValueError:
            pass
        return ""

        
    def get_queryset(self):
        sid = self.kwargs.get('sid')
        subject = senses.Subject.objects.get(uuid=sid)
        qs = models.TCCPrescription.objects.select_related(
            'compound',
            'status') .filter(
            subject=subject,
            status__name=med_const.PRESCRIPTION_STATUS__ACTIVE) .prefetch_related(
            Prefetch(
                'prescriptionevent_set',
                queryset=med_models.PrescriptionEvent.objects.filter(
                    etype__name__in=[
                        med_const.EVENT_TYPE__PRESCRIBED,
                        med_const.EVENT_TYPE__END,
                    ]) .select_related("etype") .order_by("timepoint")),
            Prefetch(
                'prescriptionevent_set',
                queryset=med_models.PrescriptionEvent.objects.filter(
                    etype__name__in=[
                        med_const.EVENT_TYPE__ADDED,
                    ]) .select_related("etype") .order_by("timepoint"),
                to_attr="added_on"),
            'compound__indications',
            'compound__active_components') .order_by(
            'compound__name',
            'status')

        return qs

    def get_context_data(self, **kwargs):
        context = super(TCCPrescriptionListView, self).get_context_data(**kwargs)
        sid = self.kwargs.get('sid')
        subject = senses.Subject.objects.get(uuid=sid)
        inactive_qs = models.TCCPrescription.objects.select_related(
            'compound',
            'status') .filter(
            subject=subject,
            status__name=med_const.PRESCRIPTION_STATUS__INACTIVE) .prefetch_related(
            Prefetch(
                'prescriptionevent_set',
                queryset=med_models.PrescriptionEvent.objects.filter(
                    etype__name__in=[
                        med_const.EVENT_TYPE__ADDED,
                        med_const.EVENT_TYPE__CANCELED,
                        med_const.EVENT_TYPE__REPLACED]) .select_related("etype") .order_by("timepoint")),
            Prefetch(
                'prescriptionevent_set',
                queryset=med_models.PrescriptionEvent.objects.filter(
                    etype__name__in=[
                        med_const.EVENT_TYPE__PRESCRIBED,
                        med_const.EVENT_TYPE__END,
                    ]) .select_related("etype") .order_by("timepoint"),
                to_attr="prescribed_info"),
            'compound__indications',
            'compound__active_components') .order_by(
            'compound__name',
            'status')
        context["inactive_prescriptions"] = inactive_qs

        # handling too many schedules for displayable_taking 
        for prescr in context["inactive_prescriptions"]:
            takings = models.ScheduledTaking.objects.filter(takings_set__id=prescr.id, active=True)
            taking_strings = []
            for taking in takings:
                taking_strings.append(taking.get_displayable())
            seperator = " | "
            displayable_taking = seperator.join(taking_strings)
            prescr.displayable_taking = displayable_taking
        for prescr in context["active_prescriptions"]:
            takings = models.ScheduledTaking.objects.filter(takings_set__id=prescr.id, active=True)
            taking_strings = []
            for taking in takings:
                taking_strings.append(taking.get_displayable())
            seperator = " | "
            displayable_taking = seperator.join(taking_strings)
            prescr.displayable_taking = displayable_taking

        context["status"] = {"inactive": med_const.PRESCRIPTION_STATUS__INACTIVE,
                             "hidden": med_const.PRESCRIPTION_STATUS__HIDDEN}
        context["enddatekey"] = med_const.EVENT_TYPE__END
        context["prescription_profiles_active"] = settings.KIOLA_PRESCRIPTION_PROFILES_ENABLED
        pprelation = med_models.PrescriptionProfileRelation.objects.filter(active=True,
                                                                       root_profile__subject=subject)
        context["active_profile_relation"] = pprelation
        if len(pprelation) > 0:
            context["active_profile_ids"] = pprelation[0].prescriptions.all().values_list("pk", flat=True)
        return context

class TCCPrescriptionView(kiola_views.KiolaSubjectView):
    fid = None
    sid = None
    template_name = 'list/tcc_prescription.html'

    def get(self, request, *args, **kwargs):
        self.fid = kwargs.get('fid', None)
        self.sid = kwargs.get('sid', None)
        return super(TCCPrescriptionView, self).get(request, *args, **kwargs)

    # override for getting back to prescription item page
    def get_success_url(self):
        """
        Returns the supplied success URL.
        """
        if self.fid:
            url = reverse('med:prescription', args=(self.request.subject_uid, self.fid))
        else:
            url = reverse('med:prescription_index', args=(self.request.subject_uid,))
        return url

    def get_form_kwargs(self):
        kwargs = super(TCCPrescriptionView, self).get_form_kwargs()
        if kwargs['initial'].get('status', None) not in [med_models.PrescriptionStatus.objects.get(name=med_const.PRESCRIPTION_STATUS__ACTIVE).pk, None]:
            kwargs.update({'_kiola_option__disabled': True})
        return kwargs

    # override for getting back to prescription item page
    def form_valid(self, form):
        try:
            self.process_form(form)
        except utils_forms.FormProcessingError:
            return self.form_invalid(form)

        if form.fid and not self.fid:
            self.fid = form.fid
        messages.success(self.request, self.get_success_message(form))
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        super(TCCPrescriptionView, self).get_context_data(**kwargs)
        # get language code of compound source
        try:
            language_code = med_models.CompoundSource.objects.filter(name=const.COMPOUND_SOURCE_NAME__TCC).order_by("pk")[0].language.terminology[:2]
        except IndexError:
            language_code = settings.LANGUAGE_CODE[0:2]

        kwargs["current_compound_source"] = med_models.CompoundSource.objects.get_default()

        pill_translated = _(med_const.TAKING_UNIT__PILL).translate(language_code).lower()
        capsule_translated = _(med_const.TAKING_UNIT__CAPSULE).translate(language_code).lower()
        search_list = [_(med_const.TAKING_UNIT__PILL).translate(language_code).lower(), _(med_const.TAKING_UNIT__CAPSULE).translate(language_code).lower()]
        pattern_list = pharmacy_models.ProductDosageForm.objects.filter(
            reduce(operator.or_, (Q(title__icontains=x) for x in search_list))).values_list(
            "title", flat=True)

        kwargs["taking_unit_mapping"] = {"pattern_list": list(pattern_list), "value": med_models.TakingUnit.objects.get(name=med_const.TAKING_UNIT__PILL).pk}
        kwargs["taking_unit_default_value"] = med_models.TakingUnit.objects.get(name=med_const.TAKING_UNIT__UNIT).pk
        if 'form' not in kwargs:
            kwargs['form'] = self.get_form()

        if kwargs["form"].initial.get('status', None) not in [med_models.PrescriptionStatus.objects.get(name=med_const.PRESCRIPTION_STATUS__ACTIVE).pk, None]:
            messages.warning(self.request, _("Prescription is readonly"))

        if self.fid:
            prescr = models.TCCPrescription.objects.select_related("unit").get(id=self.fid)
            kwargs["taking_form"] = forms.ScheduleTakingForm(initial={
                "prescription_id": self.fid, 
                "dosage": prescr.dosage, 
                "strength": prescr.strength,
                "unit": prescr.unit.name
            })
            prescription = models.TCCPrescription.objects.get(pk=self.fid)
            subject = senses.Subject.objects.get(uuid=self.sid)
            active_takings = models.ScheduledTaking.objects.filter(takings_set__id=self.fid, active=True)
            kwargs["active_takings"] = active_takings
            inactive_takings = models.ScheduledTaking.objects.filter(takings_set__id=self.fid, active=False)
            kwargs["inactive_takings"] = inactive_takings
            reactions = models.MedicationAdverseReaction.objects.filter(compound=prescription.compound, editor=subject.login)
            kwargs["reactions"] = reactions

        return kwargs


    def get_form_class(self):
        """
        Returns the form class to use in this view
        """
        # TODO:cgo:get template name from med configuration
        # site dependent
        # for now we return the only available template
        return forms.TCCPrescriptionForm
        # return self.form_class

class TakingSchemaResource(resource.Resource):

    def get(self, request, sid=None, id=None, **kwargs):
        try:
            subject = senses.Subject.objects.get(uuid=sid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")


        class Serializer(drf_serializers.ModelSerializer):
            unit = drf_serializers.CharField(source='unit.name')
            class Meta:
                model =  models.ScheduledTaking
                fields = "__all__"

        # taking_id = request.GET.get('id', None)
        taking_id = id
        if taking_id:
            try:
                taking_item = models.ScheduledTaking.objects.annotate(prescr_id=
                    F('takings_set__id')
                ).get(pk=taking_id)
            except:
                raise exceptions.BadRequest("ScheduledTaking with id '%s' does not exist" % taking_id)
            serializer = Serializer(taking_item)

        else:
            raise exceptions.BadRequest("Missing ScheduledTaking id.")

        return HttpResponse(
            JSONRenderer().render(serializer.data), 
            content_type=kiola_const.MIME_TYPE__APPLICATION_JSON, 
            status=status.HTTP_200_OK)

    def post(self, request, sid=None, id=None, fid=None, **kwargs):
        try:
            subject = senses.Subject.objects.get(uuid=sid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        form = forms.ScheduleTakingForm(request.POST)
        form.is_valid()
        data = form.cleaned_data

        taking_id = id
        prescr_id = fid
        try:
            schedule_type = "custom" if data['timepoint'].name == "custom" else "solar"
            schedule_time = data['taking_time'].strftime("%H:%M") if data['taking_time'] and data['timepoint'].name == "custom" else data['timepoint'].name
            frequency = data['frequency'].name
            reminder = data.get('reminder')
            start_date = data['start_date'].strftime("%Y-%m-%d") if data.get('start_date') else None
            end_date = data.get('end_date').strftime("%Y-%m-%d") if data.get('end_date') else None
            dose = data['dosage']
            strength = data['strength']
            unit = data['unit'].name
            hint = data.get('hint', "")
        except Exception as err:
            print('err', err)
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields " % data)
        
        taking = process_taking_request(request, data, taking_id, prescr_id, schedule_type, schedule_time, frequency, reminder, start_date, end_date, dose, strength, unit, hint, clinic_scheduled=True)

        return HttpResponse(status=status.HTTP_200_OK)

    def delete(self, request, sid=None, id=None, fid=None, **kwargs):
        taking_id = id
        prescr_id = fid
        if not taking_id:
            raise exceptions.BadRequest("Invalid request. Missing resource id")
        try:
            subject = senses.Subject.objects.get(uuid=sid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        try:
            prescr = models.TCCPrescription.objects.get(pk=prescr_id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE, subject=subject)
        except:
            raise exceptions.BadRequest("Prescription with id '%s' does not exist or is inactive" % prescr_id)

        taking = None
        try:
            taking = models.ScheduledTaking.objects.get(pk=taking_id, active=True)
        except:
            raise exceptions.BadRequest("Taking with id '%s' does not exist or is inactive" % taking_id)

        taking.active = False
        taking.save()
        update_prescription_displayable_taking(prescr)
        return HttpResponse(status=status.HTTP_200_OK)
    

# replace kiola_med.views.SISAutocompleteResource for adding PRN info
class TCCAutocompleteResource(resource.Resource):
    ''' Autocomplete Search results for SIS Database
    '''

    search_template = 'tcc_sis_search_result.html'
    max_count = 80

    @authentication.requires_api_login
    def get(self, request, **kwargs):
        """returns a rendered template of autocomplete search results
        """

        try:
            drug_search = service_providers.service_registry.search("drug_search")
        except service_providers.NoServiceFound as details:
            # FIXME : log in backend
            out = u"<span style=\"color:red\">%s</span>" % _(
                "The database for drugs is not available at the moment. Please try again later. If the problem persists, please contact our helpdesk.")
            return http.HttpResponse(out, content_type="text/html")
        try:
            drugs = drug_search(request.GET.get('q', ""))
        except service_providers.ServiceNotAvailable as details:
            # FIXME : log in backend
            msg = _("At the moment we are updating the database. Please try again later.")
            out = u"<span style=\"color:red\">%s</span>" % msg
            return http.HttpResponse(out, content_type="text/html")
        if len(drugs) > self.max_count:
            out = "<span>%s</span>" % _("More than %(max)s results found (%(amount)s). Please refine your search..").translate(
                get_language()) % {'max': self.max_count, 'amount': len(drugs)}
            return http.HttpResponse(out, content_type="text/html")
        t = get_template(self.search_template)
        html = ""
        results = []
        for drug in drugs:
            prn = models.CompoundExtraInformation.objects.filter(compound__uid=drug["unique_id"], name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE).last()
            context = {'title': drug["title"],
                       'unique_id': drug["unique_id"],
                       'main_indications': list(drug["main_indications"].values())[0],
                       'dosage_form': list(drug["dosage_form"].values())[0],
                       'active_components': u", ".join(sorted(drug["active_components"].values())),
                       'prn': prn.value if prn else None,
                       'count': drug["count"]
                       }
            results.append(t.render(context))
        html = u"<span class=\"total_count\">%s %s %s</span>\n" % (_("Found").translate(get_language()),
                                                                   len(drugs), _("results").translate(get_language()))
        html += u" (%s)\n" % (_("Click on the result to select a compound").translate(get_language()))
        html = html + "".join(results)
        return http.HttpResponse(html, content_type="text/html")
