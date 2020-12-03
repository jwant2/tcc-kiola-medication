from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic    
from django.utils import timezone

from django.contrib import messages
import csv, io
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework import viewsets, generics, mixins


from . import serializers as tcc_serializers
#from .models import MedCompound

from kiola.kiola_med.models import *
from kiola.kiola_pharmacy.models import * 

from kiola.utils import authentication
from kiola.utils.drf import KiolaAuthentication


from django.core import serializers

from kiola.utils.decorators.api import requires, returns
from kiola.utils.commons import http_client_codes
from kiola.utils import const as kiola_const

from kiola.utils.authentication import requires_api_login

from kiola.kiola_senses import resource


#testing meds
from kiola.utils import views as kiola_views
from kiola.kiola_senses import models as senses

from django.db.models import Q, Prefetch, Subquery, OuterRef, F
get_for_model = ContentType.objects.get_for_model
from django.template.response import TemplateResponse
from reversion import models as reversion


from kiola.utils.commons import get_system_user
from reversion import revisions as reversionrevisions
from reversion import models as re_models
import dateutil.parser

#pagination:
import rest_framework.pagination
from rest_framework.pagination import PageNumberPagination
from .utils import PaginationHandlerMixin, set_default_user_pref_med_time_values
from rest_framework.renderers import JSONRenderer
from kiola.kiola_med import models as med_models
from kiola.kiola_med import const as med_const
from kiola.kiola_med import utils as med_utils
from kiola.utils import exceptions

from . import models, const, utils, docs
#
from rest_framework.authentication import SessionAuthentication, BaseAuthentication
from rest_framework.permissions import IsAuthenticated

from drf_yasg.utils import swagger_auto_schema, swagger_serializer_method
from drf_yasg import openapi

from django.db import transaction

def index(request):
    from reversion_compare.mixins import CompareMixin

    qs2 = re_models.Version.objects.get_for_object_reference(med_models.Prescription, 65).order_by('pk').annotate(date_created=F('revision__date_created'))

    # print('test1,', test1)
    mixin = CompareMixin()
    compare_data, has_unfollowed_fields = mixin.compare(qs2[4].object, qs2[3], qs2[4])
    print('compare_data', compare_data)
    # print()
    # print('raw1', qs2[3].field_dict)
    # print('raw2', qs2[4].field_dict)
    for item in qs2:
        print()
        print('raw', item.field_dict)
        print('revision', item.revision)
    # se1 = tcc_serializers.MedPrescriptionSerializer(qs2[3].object)
    # se2 = tcc_serializers.MedPrescriptionSerializer(qs2[4].object)
    # print('se1', se1.data)
    # print('se2', se2.data)


    # value = { k : second_dict[k] for k in set(second_dict) - set(first_dict) }
    # print('results', results)
    return HttpResponse()

## TODO: move to admin views
def medication_upload(request):


    template =  "medicationsModule/medication_upload.html"

    prompt = {'instructions':'Upload CSV'}

    if request.method == "GET":
        return render(request,template,prompt)

    csv_file = request.FILES['file']

    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'This is not a csv file')

    data_set = csv_file.read().decode('UTF-8')
    io_string = io.StringIO(data_set)
    next(io_string)
    error_logs = []

    with transaction.atomic():
        ImportHistory.objects.filter(status="S").update(status="F")
    # lock access to this table
    with transaction.atomic():
        running_import = ImportHistory.objects.create(status="S", source_file=csv_file.name)
    with reversionrevisions.create_revision():
        reversionrevisions.set_user(get_system_user())
        name = "Prince of Wales"
        default_source_exsits = CompoundSource.objects.filter(default=True).count() > 0
        source, created = CompoundSource.objects.get_or_create(name=name,
                                  version="1.1",
                                  language=ISOLanguage.objects.get(alpha2='en'),
                                  country=ISOCountry.objects.get(alpha2="AU"),
                                  group="POW",
                                  default= False if default_source_exsits else True,
                                )

        for column in csv.reader(io_string, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL):
            try:
                if ActiveComponent.objects.filter(name=column[0]).count() == 0:
                    ac,  created = ActiveComponent.objects.get_or_create(name=column[0], name_ref=column[4])
                else:
                    ac = ActiveComponent.objects.get(name=column[0])

                dosageform=column[26]
                dosageform_ref = dosageform[:3].upper()

                if dosageform == "":
                    dosageform = "N/A"
                    dosageform_ref = "N/A"
                Product.objects.update_or_create(
                    unique_id=column[4],
                    title=column[1],
                    defaults = {
                        'title':column[1],
                        'unique_id':column[4],
                        'meta_data':'{"active_components": {"'+str(ac.id)+'":"'+ac.name+'"}, "dosage_form": {"'+dosageform_ref+'": "'+dosageform+'"}}'
                    }
                )

                compound, created = Compound.objects.update_or_create(
                    uid=column[4],
                    name=column[1],
                    defaults = {'source':source,'name':column[1],'dosage_form':column[26]}
                  )
                active_components = compound.active_components.all()
                compound.active_components.add(ac)
                compound.save()


            except Exception as error:
                error_log = {'error_msg': str(error), 'error_data': column}
                error_logs.append(error_log)

    ## FIXME: return proper info for the process result
    context = {}
    with transaction.atomic():
        # release access to this table
        running_import.status = "C"
        running_import.details = error_logs
        running_import.ended = timezone.now()
        running_import.save()
    return render(request, template, context)


class BasicPagination(PageNumberPagination):
    page_size_query_param = 'limit'

class CompoundAPIView(APIView, PaginationHandlerMixin):

    pagination_class = BasicPagination
    serializer_class = tcc_serializers.CompoundSerializer
    authentication_classes = [KiolaAuthentication,]
    max_count = 80

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
    def get(self, request, subject_uid=None, id=None, *args, **kwargs):
        
        template = med_models.Compound.objects.select_related('source')


        if id:
            qs = template.filter(uid=id)
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
                if len(compound_name) < 3:
                    msg = {'message': "Please enter at least 3 characters for better search results."}
                    return Response(msg, status=status.HTTP_200_OK)
                qs = template.filter(source__default=True, name__icontains=compound_name)

            elif active_component:
                if len(active_component) < 3:
                    msg = {'message': "Please enter at least 3 characters for better search results."}
                    return Response(msg, status=status.HTTP_200_OK)
                qs = template.filter(source__default=True, active_components__name__icontains=active_component)

            else:
                 qs = template.filter(source__default=True)

            if qs.count() > self.max_count:
                msg = {'message': "More than %(max)s results found (%(amount)s). Please refine your search.." % {'max': self.max_count, 'amount': qs.cound()}}
                return Response(msg, status=status.HTTP_200_OK)



            page = self.paginate_queryset(qs)

            if page is not None:
                serializer = self.get_paginated_response(self.serializer_class(page,
    many=True).data)

            else:
                serializer = self.serializer_class(qs, many=True)
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



# class AdverseReactionAPIView(APIView):

#     authentication_classes = [KiolaAuthentication,]
#     render_classes = [JSONRenderer,]
#     serializer_class = tcc_serializers.PatientAdverseReactionSerializer

#     @swagger_auto_schema(
#         tags=['PatientAdverseReaction'], 
#         operation_description="GET /prescription/adverse_reaction/",
#         operation_summary="Query PatientAdverseReaction",
#         responses={
#             '200': openapi.Schema(
#                 type=openapi.TYPE_ARRAY,
#                 items=openapi.Schema(
#                 type=openapi.TYPE_OBJECT,
#                     properties={
#                         "pk": openapi.Schema(type=openapi.TYPE_NUMBER, description='PatientAdverseReaction Id'),
#                         "uid": openapi.Schema(type=openapi.TYPE_NUMBER, description='PatientAdverseReaction Uid'),
#                         "substance": openapi.Schema(type=openapi.TYPE_NUMBER, description='substance for AdverseReaction'),
#                         "reactionType": openapi.Schema(type=openapi.TYPE_STRING, description='Type of adverse reaction - Allergy/Side Effect/Intolerance/Idiosyncratic/Unknown'),
#                         "reactions": openapi.Schema(type=openapi.TYPE_STRING, description='reaction details'),
#                         "created": openapi.Schema(type=openapi.TYPE_STRING, description='created time of this reaction item  '),
#                         "updated": openapi.Schema(type=openapi.TYPE_STRING, description='updated time of this reaction item '),
#                         "active": openapi.Schema(type=openapi.TYPE_STRING, description='Status of this reaction item - false indicates deleted'),

#             })),
#             '400': "Bad Request"
#         }
#     )
#     @requires_api_login
#     def get(self, request, subject_uid=None, pk=None, *args, **kwargs):
#         try:
#             if subject_uid is None:
#                 subject = senses.Subject.objects.get(login=request.user)
#             else:
#                 subject = senses.Subject.objects.get(uuid=subject_uid)
#         except senses.Subject.DoesNotExist:
#             raise exceptions.Forbidden("Unknown subject")

#         reaction_id = pk
#         if reaction_id:
#             try:
#                 reaction_item = models.PatientAdverseReaction.objects.get(pk=reaction_id)
#             except Exception as err:
#                 print(err)
#                 raise exceptions.BadRequest("PatientAdverseReaction with pk '%s' does not exist" % reaction_id)
#             serializer = self.serializer_class(reaction_item)
#         else:
#             qs = models.PatientAdverseReaction.objects.filter(subject=subject, active=True)
#             serializer = self.serializer_class(qs, many=True)

#         return Response(serializer.data, status=status.HTTP_200_OK)

#     @swagger_auto_schema(
#         tags=['PatientAdverseReaction'], 
#         operation_description="GET /prescription/adverse_reaction/",
#         operation_summary="Create/update PatientAdverseReaction",
#         request_body=openapi.Schema(
#                 type=openapi.TYPE_OBJECT,
#                 properties={
#                     "substance": openapi.Schema(type=openapi.TYPE_NUMBER, description='substance for AdverseReaction'),
#                     "reactionType": openapi.Schema(type=openapi.TYPE_STRING, description='Type of adverse reaction - Allergy/Side Effect/Intolerance/Idiosyncratic/Unknown'),
#                     "reactions": openapi.Schema(type=openapi.TYPE_STRING, description='reaction details'),
#                     "active": openapi.Schema(type=openapi.TYPE_STRING, description='Status of this reaction item - false indicates deleted'),
#                 },
#         ),
#         responses={
#             '200': openapi.Schema(
#                 type=openapi.TYPE_ARRAY,
#                 items=openapi.Schema(
#                 type=openapi.TYPE_OBJECT,
#                     properties={
#                         "pk": openapi.Schema(type=openapi.TYPE_NUMBER, description='PatientAdverseReaction Id'),
#                         "uid": openapi.Schema(type=openapi.TYPE_NUMBER, description='PatientAdverseReaction Uid'),
#                         "substance": openapi.Schema(type=openapi.TYPE_NUMBER, description='substance for AdverseReaction'),
#                         "reactionType": openapi.Schema(type=openapi.TYPE_STRING, description='Type of adverse reaction - Allergy/Side Effect/Intolerance/Idiosyncratic/Unknown'),
#                         "reactions": openapi.Schema(type=openapi.TYPE_STRING, description='reaction details'),
#                         "created": openapi.Schema(type=openapi.TYPE_STRING, description='created time of this reaction item  '),
#                         "updated": openapi.Schema(type=openapi.TYPE_STRING, description='updated time of this reaction item '),
#                         "active": openapi.Schema(type=openapi.TYPE_STRING, description='Status of this reaction item - false indicates deleted'),

#             })),
#             '400': "Bad Request"
#         }
#     )
#     @requires_api_login
#     def post(self, request, subject_uid=None, pk=None, *args, **kwargs):
#         try:
#             if subject_uid is None:
#                 subject = senses.Subject.objects.get(login=request.user)
#             else:
#                 subject = senses.Subject.objects.get(uuid=subject_uid)
#         except senses.Subject.DoesNotExist:
#             raise exceptions.Forbidden("Unknown subject")
        
#         data = request.data
#         substance_value = data.get('substance', "")
#         reaction_type_value = data.get('reactionType', "")
#         reactions_value = data.get('reactions', "")
#         # reaction_id = data.get('uid', None)
#         reaction_id = pk
#         active_value = data.get('active', None)

#         if substance_value == "" or reactions_value == "" or (active_value is not None and type(active_value) != type(True)):
#             raise exceptions.BadRequest("Invalid data %s " % data)
        
#         if active_value is None:
#             active_value = True

#         try:
#             reaction_type = models.AdverseReactionType.objects.get(name=reaction_type_value)
#         except:
#             raise exceptions.BadRequest("Invalid value %s for reaction_type" % reaction_type_value)
        
#         if reaction_id:
#             try:
#                 adverse_reaction = models.PatientAdverseReaction.objects.get(pk=reaction_id, active=True)
#             except:
#                 raise exceptions.BadRequest("Adverse Reaction with pk %s does not exist or has been deleted" % reaction_id)

#             adverse_reaction.substance = substance_value
#             adverse_reaction.reaction_type = reaction_type
#             adverse_reaction.reactions = reactions_value
#             adverse_reaction.active = active_value
#             adverse_reaction.save()

#         else:
#             adverse_reaction = models.PatientAdverseReaction.objects.create(
#                     subject=subject,
#                     substance=substance_value, 
#                     reaction_type=reaction_type,
#                     reactions=reactions_value,
#                     active=active_value,
#                     )


#         serializer = self.serializer_class([adverse_reaction], many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)


# class PrescriptionQueryAPIView(APIView):

#     authentication_classes = [KiolaAuthentication,]
#     render_classes = [JSONRenderer,]
#     serializer_class = tcc_serializers.MedPrescriptionSerializer

class PrescriptionAPIView(APIView):

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

        # prescr_id = request.GET.get('id', None)
        prescr_id = id
        if prescr_id:
            try:
                prescr = med_models.Prescription.objects.select_related(
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
                raise exceptions.BadRequest("Prescription with pk '%s' does not exist or is inactive" % prescr_id)
            serializer = self.serializer_class([prescr], many=True)

        else:

            qs = med_models.Prescription.objects.select_related(
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

            serializer = self.serializer_class(qs, many=True)

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

        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        

        prescr_id = id
        # prescr_id = data.get('id', None)

        # filter extra fields that are not allowed for storing history records
        def process_request_data(request_data):
            data = {
              'compound': request_data.get('compound', None),
              'reason': request_data.get('reason', ""),
              'hint': request_data.get('hint', ""),
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
        active = processed_data.get('active', None)  
        # med_reactions = processed_data.get("medicationAdverseReactions", "")
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
        if active is not None and type(active) != bool:
            raise exceptions.BadRequest("Invalid data '%s' " % processed_data)
        if prescr_id:
            try:
                prescr = med_models.Prescription.objects.get(pk=prescr_id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
                
            except:
                raise exceptions.BadRequest("Prescription with id '%s' does not exist or is inactive" % prescr_id)

            if prescr.compound.uid != compound_obj['id']:
                raise exceptions.BadRequest("Compound with id '%s' does not match the compound of the given prescription with pk '%s'" % (compound_obj['id'], prescr_id))

            # update_or_create_med_adverse_reaction(request, med_reactions, prescr.compound)
            update_or_create_med_type(request, medication_type, prescr)

            with reversionrevisions.create_revision():
                reversionrevisions.set_user(get_system_user())

            start = prescr.prescriptionevent_set.filter(etype=med_models.PrescriptionEventType.objects.get(name=med_const.EVENT_TYPE__PRESCRIBED))[0]
            start.timepoint = start_date
            start.save()
            end = prescr.prescriptionevent_set.filter(etype=med_models.PrescriptionEventType.objects.get(name=med_const.EVENT_TYPE__END))
            if len(end) > 0 and end_date:
                end[0].timepoint =end_date
                end[0].save()

            prescr.taking_hint = taking_hint
            prescr.taking_reason =  taking_reason
            if active is not None and active is False:
                prescr_stauts_inactive = med_models.PrescriptionStatus.objects.get(name=med_const.PRESCRIPTION_STATUS__INACTIVE)
                prescr.status = prescr_stauts_inactive
            prescr.save()


        else:
            p_status = med_models.PrescriptionStatus.objects.get(name="Active")
            compound = med_models.Compound.objects.filter(uid=compound_obj['id'], source__default=True).last()
            if not compound or compound.source.default is not True:
                raise exceptions.BadRequest("Compound with id '%s' does not exist or its source is inactive" % compound_obj['id'])

            # update_or_create_med_adverse_reaction(request, med_reactions, compound)

            with reversionrevisions.create_revision():
                reversionrevisions.set_user(get_system_user())
                prescr, replaced = med_models.Prescription.objects.prescribe(subject=subject,
                                                                          prescriber=request.user,
                                                                          compound=compound,
                                                                          reason=taking_reason,
                                                                          hint=taking_hint,
                                                                          taking=med_utils.TakingSchemaText(""),
                                                                          start=start_date,
                                                                          end=end_date)

            update_or_create_med_type(request, medication_type, prescr)

        # save change history
        if processed_data.get('id', None) is None:
            processed_data['id'] = str(prescr.pk)
        record = models.MedicationRelatedHistoryData.objects.add_data_change_record(prescr, processed_data)
        # prepare object for response
        prescr = med_models.Prescription.objects.get(pk=prescr.pk)
        serializer = self.serializer_class([prescr], many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

def update_or_create_med_adverse_reaction(request, reactions_str: str, compound: med_models.Compound):
    reactions = reactions_str.split(',')
    reaction_type = models.AdverseReactionType.objects.get(name=const.ADVERSE_REACTION_TYPE__UNKNOWN)
    for item in reactions:
        exist = models.MedicationAdverseReaction.objects.filter(compound=compound, reactions=reactions, editor=request.user).count()
        if exist == 0 and item != "":
            reaction_item, created = models.MedicationAdverseReaction.objects.get_or_create(
                compound=compound, reaction_type=reaction_type, reactions=item, editor=request.user)

def update_or_create_med_type(request, medication_type: str, prescription: med_models.Prescription):

    prn, created = models.PrescriptionExtraInformation.objects.get_or_create(prescription=prescription, name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE)
    prn.value = medication_type
    prn.save()
    return prn

class PrescriptionHistoryAPIView(APIView):

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
            prescr = med_models.Prescription.objects.select_related('compound').get(pk=id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
        except Exception as err:
            print(err)
            raise exceptions.BadRequest("Prescription with id '%s' does not exist or is inactive" % id)

        qs = models.MedicationRelatedHistoryData.objects.get_history_data(prescr)


        results = []
        for i in range(len(qs) - 1):
            A = qs[i].data
            B = qs[i+1].data 
            value = {x:(A[x], B[x]) for x in B if x in A if B[x] != A[x]}
            print('value', value)
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

        return Response(results, status=status.HTTP_200_OK)



class MedicationAdverseReactionAPIView(APIView):

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
            serializer = self.serializer_class([reaction_item], many=True)

        else:
            qs = models.MedicationAdverseReaction.objects.filter(
              compound__pk__in=med_models.Prescription.objects.select_related(
                'compound',
                'status') .filter(
                subject=subject,
                status__name=med_const.PRESCRIPTION_STATUS__ACTIVE).values_list('compound__pk', flat=True)
            )
            print('qs', qs)
            serializer = self.serializer_class(qs, many=True)
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
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        data = request.data
        # reaction_id = data.get('uid', None)
        reaction_id = id
        prescr_id = data.get('medicationId', None)
        reaction_type_name = data.get('reactionType', None)
        reactions = data.get('reactions', None)
        active = data.get('active', None)

        if not prescr_id or not reaction_type_name or not reactions:
            raise exceptions.BadRequest("Invalid data '%s' " % data)
        if active is not None and type(active) != bool:
            raise exceptions.BadRequest("Invalid data '%s' " % data)

        try:
            prescr = med_models.Prescription.objects.select_related('compound').get(pk=prescr_id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
        except:
            raise exceptions.BadRequest("Prescription with id '%s' does not exist or is inactive" % prescr_id)
          
        try:
            reaction_type = models.AdverseReactionType.objects.get(name=reaction_type_name)
        except:
            raise exceptions.BadRequest("AdverseReactionType with name '%s' does not exist" % reaction_type_name)

        compound = prescr.compound

        if reaction_id:
            try:
                reaction_item = models.MedicationAdverseReaction.objects.get(uid=reaction_id)
                reaction_item.compound = compound
                reaction_item.reaction_type = reaction_type
                reaction_item.reactions = reactions
                reaction_item.editor = request.user
                if active is not None:
                    reaction_item.active = active
                reaction_item.save()
            except:
                raise exceptions.BadRequest("MedicationAdverseReaction with id '%s' does not exist" % reaction_id)

        else:
            reaction_item, created = models.MedicationAdverseReaction.objects.get_or_create(
                compound=compound, reaction_type=reaction_type, reactions=reactions, editor=request.user, active=True)

        serializer = self.serializer_class([reaction_item], many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
        

class TakingSchemaAPIView(APIView):

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
                    F('takingschema__prescriptionschema__prescription')
                ).get(pk=taking_id)
            except Exception as err:
                print(err)
                raise exceptions.BadRequest("ScheduledTaking with id '%s' does not exist" % taking_id)
            serializer = self.serializer_class([taking_item], many=True)

        else:
            taking_qs = (
                models.ScheduledTaking.objects.filter(
                    takingschema__prescriptionschema__prescription__subject=subject,
                    takingschema__prescriptionschema__prescription__status__name=med_const.PRESCRIPTION_STATUS__ACTIVE,
                )
                .annotate(prescr_id=
                    F('takingschema__prescriptionschema__prescription')
                )
            )
            serializer = self.serializer_class(taking_qs, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


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


        data = request.data
        # taking_id = data.get('id', "")

        taking_id = id
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
            active = data.get('active', None)

        except: 
            raise exceptions.BadRequest("Invalid data '%s'. Missing some of the required fields " % data)

        if active is not None and type(active) != bool:
            raise exceptions.BadRequest("Invalid data '%s' " % data)

        taking = None
        if taking_id:
            try:
                taking = models.ScheduledTaking.objects.get(pk=taking_id)
            except:
                raise exceptions.BadRequest("Taking with id '%s' does not exist " % taking_id)

        try:
            prescr = med_models.Prescription.objects.get(pk=prescr_id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
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
            if active is not None and active is False:
                schema = prescr_schema.taking_schema
                schema.takings.remove(taking)
                schema.save()
                # order_taking = med_models.OrderedTaking.objects.get(taking=taking, schema=schema)
                # order_taking.delete()

            else:

                taking.timepoint=timepoint
                taking.taking_time=time
                taking.start_date=datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
                taking.end_date=datetime.strptime(end_date.split("T")[0], "%Y-%m-%d") if end_date else None
                taking.editor=request.user
                taking.unit=taking_unit
                taking.strength=strength
                taking.dosage=dose
                taking.reminder=reminder
                taking.clinic_scheduled=False
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
                clinic_scheduled=False,
                frequency=models.TakingFrequency.objects.get(name=frequency)
            )
  
            if should_new_takingschema:
                schema = med_models.TakingSchema.objects.create()
                med_models.OrderedTaking.objects.create(taking=taking, schema=schema)
                schema.save()
                prescr_schema.taking_schema = schema
                prescr_schema.save()
            else:
                schema = prescr_schema.taking_schema
                ## FIXME: need to check if there is an existing taking for same prescr and timepoint?
                med_models.OrderedTaking.objects.create(taking=taking, schema=schema)
                schema.save()
        
        serializer = self.serializer_class([models.ScheduledTaking.objects.annotate(prescr_id=
                    F('takingschema__prescriptionschema__prescription')
                ).get(pk=taking.pk)], many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

class UserPreferenceConfigAPIView(APIView):
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

        data = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user)
        if data is None: 
            set_default_user_pref_med_time_values(request.user)
            data = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user)
        config_data = data.values()
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
        
        med_pref_data = request.data
        config_data = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user)
        for item in med_pref_data:
            config_item = config_data.get(f'{const.USER_PREFERENCE_CONFIG_PREFIX}{item["type"]}', None)
            if config_item is None:
                raise exceptions.BadRequest("Invalid data for type '%s" % item['type'])
            config_data[f'{const.USER_PREFERENCE_CONFIG_PREFIX}{item["type"]}'] = item
        result = models.UserPreferenceConfig.objects.set_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, config_data, request.user)
        config_data = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user).values()
        return Response(config_data, status=status.HTTP_200_OK)


