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

from . import models, const, utils
#
from rest_framework.authentication import SessionAuthentication, BaseAuthentication
from rest_framework.permissions import IsAuthenticated
#
def index(request):
    return HttpResponse("Hello, world. You're at the medicationsModule index.")

def addCompoundSource(request):
    name = "Prince of Wales"
    CompoundSource.objects.get_or_create(name=name,
                                  version="1.0",
                                  language=ISOLanguage.objects.get(alpha2='en'),
                                  country=ISOCountry.objects.get(alpha2="AU"),
                                  group="POW"
                                )
    return HttpResponse("Hello, world. You're at compoundSource.")


from django.db import transaction

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
                print('error', error)
                print('error for ', column)
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


class prescriptions(APIView):
    authentication_classes = [KiolaAuthentication,]
    @requires_api_login
    def get (self,request,format=None):
        an_apiview = [
            'Uses HTTPS methods',
            'Mapped manually to URLs'
        ]
        return Response({'message':'Hello!','an_apiview':an_apiview})


class compounds(APIView):

    @authentication.requires_api_login
    def get (self,request,format=None):

        an_apiview = [
            'Uses HTTPS methods',
            'Mapped manually to URLs'
        ]

        return Response({'message':'Hello!','an_apiview':an_apiview})


#working auth with text httpresponse:
# class CompoundAPIView(APIView):

#     authentication_classes = [KiolaAuthentication,]
#     @requires_api_login
#     def get(self, request, **kwargs):
        # return HttpResponse("Request was successful.")

class BasicPagination(PageNumberPagination):
    page_size_query_param = 'limit'

class CompoundAPIView(APIView, PaginationHandlerMixin):

    pagination_class = BasicPagination
    serializer_class = tcc_serializers.CompoundSerializer
    authentication_classes = [KiolaAuthentication,]
    @requires_api_login
    def get(self, request, subject_uid=None,uid=None, *args, **kwargs):
        
        qs = Compound.objects.all()

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
            data = {
                "enabled_profile": [
                    {"id": root_profile.name}
                ]
            }
            children = root_profile.children.all()
            if len(children) > 0:
                data['enabled_profile'][0]['children'] = []
                for child in children:

                    data['enabled_profile'][0]['children'].append({
                        "id": child.name
                    })
        else:
            data = {
                "enabled_profile": []
            }

        return Response(data, status=status.HTTP_200_OK)

class CompoundRudView(generics.RetrieveUpdateDestroyAPIView): # DetailView CreateView FormView
    lookup_field            = 'pk' 
    serializer_class        = tcc_serializers.CompoundaSerializer

    

    @authentication.requires_api_login
    def get_queryset(self):
        return Compound.objects.all()

    @authentication.requires_api_login
    def get_serializer_context(self, *args, **kwargs):
        return {"request": self.request}


class PrescriptionRudView(generics.RetrieveUpdateDestroyAPIView): # DetailView CreateView FormView
    lookup_field            = 'subject_id' 
    serializer_class        = tcc_serializers.PrescriptionSerializer

    

    @authentication.requires_api_login
    def get_queryset(self):
        qs = Prescription.objects.all()
        query = self.request.GET.get("q")
        if query is not None:
            qs = qs.filter(
                    Q(title__icontains=query)|
                    Q(content__icontains=query)
                    ).distinct()
        return qs

    @authentication.requires_api_login
    def get_serializer_context(self, *args, **kwargs):
        return {"request": self.request}



#MEDS TESTING:
class PrescriptionListView(kiola_views.KiolaSubjectListView):
    #title = _("Prescriptions")
    # template_name = 'lists/prescription_list.html'
    # addurl_name = 'med:prescription_add'
    # context_object_name = 'active_prescriptions'

    def get_queryset(self):
        
        sid = self.kwargs.get('sid')
        subject = senses.Subject.objects.get(uuid=sid)
        
        qs = med_models.Prescription.objects.select_related('compound', 'status')\
                                        .filter(subject=subject,
                                                status__name=const.PRESCRIPTION_STATUS__ACTIVE)\
                                        .prefetch_related(Prefetch('prescriptionevent_set',
                                                                   queryset=med_models.PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__PRESCRIBED,
                                                                                                                            const.EVENT_TYPE__END, ])\
                                                                                                            .select_related("etype")\
                                                                                                            .order_by("timepoint")),
                                                          Prefetch('prescriptionevent_set',
                                                                   queryset=med_models.PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__ADDED, ])\
                                                                                                            .select_related("etype")\
                                                                                                            .order_by("timepoint"),
                                                                    to_attr="added_on"),
                                                          'compound__indications',
                                                          'compound__active_components')\
                                        .order_by('compound__name',
                                                  'status')

        return qs

    def get_context_data(self, **kwargs):
        context = super(PrescriptionListView, self).get_context_data(**kwargs)
        sid = self.kwargs.get('sid')
        subject = senses.Subject.objects.get(uuid=sid)
        qs = med_models.Prescription.objects.select_related('compound', 'status')\
                                        .filter(subject=subject,
                                                status__name=const.PRESCRIPTION_STATUS__INACTIVE)\
                                        .prefetch_related(Prefetch('prescriptionevent_set',
                                                                    queryset=med_models.PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__ADDED,
                                                                                                                                      const.EVENT_TYPE__CANCELED,
                                                                                                                                      const.EVENT_TYPE__REPLACED])\
                                                                                                      .select_related("etype")\
                                                                                                      .order_by("timepoint")),
                                                          Prefetch('prescriptionevent_set',
                                                                   queryset=med_models.PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__PRESCRIBED,
                                                                                                                                     const.EVENT_TYPE__END,
                                                                                                                                     ])\
                                                                                                            .select_related("etype")\
                                                                                                            .order_by("timepoint"),
                                                                    to_attr="prescribed_info"),

                                                          'compound__indications',
                                                          'compound__active_components'
                                                                           )\
                                        .order_by('compound__name',
                                                  'status')
        context["inactive_prescriptions"] = qs
        context["status"] = {"inactive":const.PRESCRIPTION_STATUS__INACTIVE,
                             "hidden":const.PRESCRIPTION_STATUS__HIDDEN}
        context["enddatekey"] = const.EVENT_TYPE__END
        context["prescription_profiles_active"] = settings.KIOLA_PRESCRIPTION_PROFILES_ENABLED
        pprelation = med_models.PrescriptionProfileRelation.objects.filter(active=True,
                                                          root_profile__subject=subject)
        context["active_profile_relation"] = pprelation
        if len(pprelation) > 0:
            context["active_profile_ids"] = pprelation[0].prescriptions.all().values_list("pk", flat=True)
        return context







##FROM MEDS:
class PrescriptionListAPI(resource.Resource):
    authentication_classes = (KiolaAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    @authentication.requires_api_login
    # @api.returns(status_codes={ codes.OK : "OK" , },
    #          content_types=[kiola_const.MIME_TYPE__TEXT_HTML, ])
    def get(self, request, **kwargs):

        subject = senses.Subject.objects.get(login=request.user)
       
        qs = Prescription.objects.select_related('compound',
            'status').filter(subject=subject,
                             status__name=const.PRESCRIPTION_STATUS__ACTIVE).order_by('status',
                                        'compound__name').prefetch_related('prescriptionevent_set',
                                                                           'prescriptionevent_set__etype',
                                                                           'compound__indications',
                                                                           'compound__active_components'
                                                                           )

        qs = Prescription.objects.select_related('compound', 'status')\
                                        .filter(subject=subject,
                                                status__name=const.PRESCRIPTION_STATUS__ACTIVE)\
                                        .prefetch_related(Prefetch('prescriptionevent_set',
                                                                   queryset=PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__PRESCRIBED,
                                                                                                                                     const.EVENT_TYPE__END, ])\
                                                                                                            .select_related("etype")\
                                                                                                            .order_by("timepoint")),
                                                          Prefetch('prescriptionevent_set',
                                                                   queryset=PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__ADDED, ])\
                                                                                                            .select_related("etype")\
                                                                                                            .order_by("timepoint"),
                                                                    to_attr="added_on"),
                                                          'compound__indications',
                                                          'compound__active_components')\
                                        .order_by('compound__name',
                                                  'status')
        qs_json = serializers.serialize('json', qs)
        return HttpResponse(qs_json, content_type='application/json')

    @authentication.requires_api_login
    @requires(accepts=["application/json", ])
    def post(self, request, **kwargs):
        
        data = json.loads(request.body.decode("utf-8"))

        #adapter = Compound.objects.get_adapter(CompoundSource.objects.get(name="Prince of Dales").id)
        #compound, created = adapter.get_or_create(data["compound_id"])
        compound = Compound.objects.filter(uid=data["compound_id"]).filter(source_id=CompoundSource.objects.get(name="Prince of Wales").id)[0]
        
        subject = senses.Subject.objects.get(login=request.user)


        if data["taking__text"] not in ["", None]:
            taking = utils.TakingSchemaText(data["taking__text"])
        else:
            taking = utils.TakingSchemaStandard(str(data["taking__morning"] or 0),
                                                str(data["taking__noon"] or 0),
                                                str(data["taking__evening"]or 0),
                                                str(data["taking__night"] or 0),
                                                TakingUnit.objects.get(pk=data["taking__unit"]))
        subject=subject
        compound=compound
        reason=data.get("taking__reason", None)
        hint=data.get("taking__hint", None)
        taking=taking
        start=dateutil.parser.parse(data["ev__prescription_startdate"])
        end=dateutil.parser.parse(data.get("ev__prescription_enddate", None))

        #Permissions working here with reversionrevisions, but need to add more than just to Prescription model:
        # with reversionrevisions.create_revision():
        #     reversionrevisions.set_user(get_system_user())
            
        #     Prescription.objects.create(compound=compound,
        #                            status=PrescriptionStatus.objects.get(name=const.PRESCRIPTION_STATUS__ACTIVE),
        #                            subject=subject,
        #                            taking_reason=reason,
        #                            taking_hint=hint)



        with reversionrevisions.create_revision():
            reversionrevisions.set_user(get_system_user())
            
            prescription, replaced = Prescription.objects.prescribe(subject=subject,
                                                                       prescriber=request.user,
                                                                       compound=compound,
                                                                       reason=data.get("taking__reason", None),
                                                                       hint=data.get("taking__hint", None),
                                                                       taking=taking,
                                                                       start=dateutil.parser.parse(data["ev__prescription_startdate"]),
                                                                    
                                                                       end=dateutil.parser.parse(data.get("ev__prescription_enddate", None)))
        
        return HttpResponse("Post successful")


class AdverseReactionAPIView(APIView):

    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]
    serializer_class = tcc_serializers.PatientAdverseReactionSerializer

    @requires_api_login
    def get(self, request, subject_uid=None,uid=None, *args, **kwargs):
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        qs = models.PatientAdverseReaction.objects.filter(subject=subject, active=True)
        serializer = self.serializer_class(qs, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @requires_api_login
    def post(self, request, subject_uid=None,uid=None, *args, **kwargs):
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        
        data = request.data
        substance_value = data.get('substance', "")
        reaction_type_value = data.get('reaction_type', "")
        reactions_value = data.get('reactions', "")
        uid_value = data.get('uid', None)
        active_value = data.get('active', None)

        if substance_value == "" or reactions_value == "" or (active_value is not None and type(active_value) != type(True)):
            raise exceptions.BadRequest("Invalid data %s " % data)
        
        if active_value is None:
            active_value = True

        try:
            reaction_type = models.PatientAdverseReaction.objects.get(name=reaction_type_value)
        except:
            raise exceptions.BadRequest("Invalid value %s in reaction_type" % reaction_type_value)
        
        if uid_value:
            try:
                adverse_reaction = models.PatientAdverseReaction.objects.get(uid=uid_value, active=True)
            except:
                raise exceptions.BadRequest("Adverse Reaction with uid %s does not exist or has been deleted" % uid_value)

            adverse_reaction.substance = substance_value
            adverse_reaction.reaction_type = reaction_type
            adverse_reaction.reactions = reactions_value
            adverse_reaction.active = active_value
            adverse_reaction.save()

        else:
            adverse_reaction = models.PatientAdverseReaction.objects.create(
                    subject=subject,
                    substance=substance_value, 
                    reaction_type=reaction_type,
                    reactions=reactions_value,
                    active=active_value,
                    )


        serializer = self.serializer_class([adverse_reaction], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# class PrescriptionQueryAPIView(APIView):

#     authentication_classes = [KiolaAuthentication,]
#     render_classes = [JSONRenderer,]
#     serializer_class = tcc_serializers.MedPrescriptionSerializer


class PrescriptionAPIView(APIView):

    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]
    serializer_class = tcc_serializers.MedPrescriptionSerializer

    @requires_api_login
    def get(self, request, subject_uid=None,uid=None, *args, **kwargs):

        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        prescr_id = request.GET.get('id', None)
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
                'status') .annotate(adverse_reactions=Subquery(
                    models.MedicationAdverseReaction.objects.filter(
                        compound=OuterRef('compound'),
                        active=True
                    ).values_list('reactions', flat=True)
                ))[0]


            except Exception as err:
                print(err)
                raise exceptions.BadRequest("Prescription with pk '%s' does not exist or is inactive" % prescr_id)
            serializer = self.serializer_class(prescr)

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
                'status') .annotate(adverse_reactions=Subquery(
                    models.MedicationAdverseReaction.objects.filter(
                        compound=OuterRef('compound'),
                        active=True
                    ).values_list('reactions', flat=True)
                ))

            serializer = self.serializer_class(qs, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


    @requires_api_login
    def post(self, request, subject_uid=None, *args, **kwargs):

        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        
        data = request.data
        prescr_id = data.get('id', None)
        compound_name = data.get('compoundName', None)
        taking_reason = data.get('taking_reason', "")
        taking_hint = data.get('taking_hint', "")
        med_reactions = data.get("medicationAdverseReactions", "")
        medication_type = data.get('medicationType', None)
        p_start = data.get('prescription_start', None)
        p_end = data.get('prescription_end', None)

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

        if prescr_id:
            try:
                prescr = med_models.Prescription.objects.get(pk=prescr_id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
                
            except Exception as err:
                print(err)
                raise exceptions.BadRequest("Prescription with id '%s' does not exist or is inactive" % prescr_id)

            if prescr.compound.name != compound_name:
                raise exceptions.BadRequest("Compound with name '%s' does not match the compound of the given prescription with pk '%s'" % (compound_name, prescr_id))

            update_or_create_med_adverse_reaction(request, med_reactions, prescr.compound)
            update_or_create_med_type(request, medication_type, prescr.compound)

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
            prescr.save()


        else:
            p_status = med_models.PrescriptionStatus.objects.get(name="Active")
            compound = med_models.Compound.objects.filter(name=compound_name, source__default=True).last()
            if not compound or compound.source.default is not True:
                raise exceptions.BadRequest("Compound with name '%s' does not exist or its source is inactive" % compound_name)

            update_or_create_med_adverse_reaction(request, med_reactions, compound)
            update_or_create_med_type(request, medication_type, compound)

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



        serializer = self.serializer_class(prescr)

        return Response(serializer.data, status=status.HTTP_200_OK)

def update_or_create_med_adverse_reaction(request, reactions_str: str, compound: med_models.Compound):
    reactions = reactions_str.split(',')
    reaction_type = models.AdverseReactionType.objects.get(name=const.ADVERSE_REACTION_TYPE__UNKNOWN)
    for item in reactions:
        exist = models.MedicationAdverseReaction.objects.filter(compound=compound, reactions=reactions, editor=request.user).count()
        if exist == 0 and item != "":
            reaction_item, created = models.MedicationAdverseReaction.objects.get_or_create(
                compound=compound, reaction_type=reaction_type, reactions=item, editor=request.user)

def update_or_create_med_type(request, medication_type: str, compound: med_models.Compound):

    prn, created = models.CompoundExtraInformation.objects.get_or_create(compound=compound, name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE)
    prn.value = medication_type
    prn.save()
    return prn

class MedicationAdverseReactionAPIView(APIView):

    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]
    serializer_class = tcc_serializers.MedicationAdverseReactionSerializer

    @requires_api_login
    def get(self, request, subject_uid=None, *args, **kwargs):
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        reaction_id = request.GET.get('id', None)
        if reaction_id:
            try:
                reaction_item = models.MedicationAdverseReaction.objects.get(pk=reaction_id)
            except Exception as err:
                print(err)
                raise exceptions.BadRequest("MedicationAdverseReaction with pk '%s' does not exist" % reaction_id)
            serializer = self.serializer_class(reaction_item)

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


    @requires_api_login
    def post(self, request, subject_uid=None, *args, **kwargs):  
        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        data = request.data
        reaction_id = data.get('uid', None)
        prescr_id = data.get('medicationId', None)
        reaction_type_name = data.get('reactionType', None)
        reactions = data.get('reactions', None)

        if not prescr_id or not reaction_type_name or not reactions:
            raise exceptions.BadRequest("Invalid data '%s' " % data)

        try:
            prescr = med_models.Prescription.objects.select_related('compound').get(pk=prescr_id, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)
        except Exception as err:
            print(err)
            raise exceptions.BadRequest("Prescription with pk '%s' does not exist or is inactive" % prescr_id)

        try:
            reaction_type = models.AdverseReactionType.objects.get(name=reaction_type_name)
        except Exception as err:
            print(err)
            raise exceptions.BadRequest("AdverseReactionType with name '%s' does not exist" % reaction_type_name)

        compound = prescr.compound

        if reaction_id:
            try:
                reaction_item = models.MedicationAdverseReaction.objects.get(uid=reaction_id)
                reaction_item.compound = compound
                reaction_item.reaction_type = reaction_type
                reaction_item.reactions = reactions
                reaction_item.editor = request.user
                reaction_item.save()
            except Exception as err:
                print(err)
                raise exceptions.BadRequest("MedicationAdverseReaction with uid '%s' does not exist" % reaction_id)

        else:
            reaction_item, created = models.MedicationAdverseReaction.objects.get_or_create(
                compound=compound, reaction_type=reaction_type, reactions=reactions, editor=request.user)

        serializer = self.serializer_class(reaction_item)

        return Response(serializer.data, status=status.HTTP_200_OK)
        

class TakingSchemaAPIView(APIView):

    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]
    serializer_class = tcc_serializers.ScheduledTakingSerializer

    @requires_api_login
    def get(self, request, subject_uid=None, pk=None, *args, **kwargs):

        try:
            if subject_uid is None:
                subject = senses.Subject.objects.get(login=request.user)
            else:
                subject = senses.Subject.objects.get(uuid=subject_uid)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")

        taking_id = request.GET.get('id', None)
        if taking_id:
            try:
                taking_item = models.ScheduledTaking.objects.get(pk=taking_id)
            except Exception as err:
                print(err)
                raise exceptions.BadRequest("ScheduledTaking with pk '%s' does not exist" % taking_id)
            serializer = self.serializer_class(taking_item)

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

    @requires_api_login
    def post(self, request, subject_uid=None, *args, **kwargs):


        data = request.data
        taking_id = data.get('id', "")
        prescr_id = data.get('medicationId', "")
        schedule = data.get('schedule', None)
        schedule_type = schedule.get('type', None)
        schedule_time = schedule.get('time', None)
        frequency = data.get('frequency', None)
        reminder = data.get('reminder', False)
        start_date = data.get('startTime', None)
        dose = data.get('dose', None)
        strength = data.get('strength', None)
        unit = data.get('formulation', None)

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
            raise exceptions.BadRequest("Prescription with pk '%s' does not exist or is inactive" % prescr_id)
        
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
        takings = prescr_schema.taking_schema.takings.all()
        print('takings', takings)
        should_new_takingschema = False
        with reversionrevisions.create_revision():
            reversionrevisions.set_user(get_system_user())
            for item in takings:
                try:
                    exist = item.scheduledtaking
                except:
                    should_new_takingschema = True
                    break

        print('should_new_takingschema', should_new_takingschema)
        print('taking', taking)
        print('time', time)

        taking_unit, created = med_models.TakingUnit.objects.get_or_create(name=unit)
        if taking:
            if taking not in takings:
                raise exceptions.BadRequest("Taking with id '%s' does not match the gvien prescription (%s)" % (taking_id, prescr_id))
            taking.timepoint=timepoint,
            taking.taking_time=time,
            taking.start_date=datetime.strptime(start_date.split("T")[0], "%Y-%m-%d"),
            taking.editor=request.user,
            taking.unit=taking_unit,
            taking.strength=strength,
            taking.dosage=dose,
            taking.reminder=reminder,
            taking.clinic_scheduled=False,
            taking.frequency=models.TakingFrequency.objects.get(name=frequency)
            taking.save() 

        else:
            taking = models.ScheduledTaking.objects.create(
                timepoint=timepoint,
                taking_time=time,
                start_date=datetime.strptime(start_date.split("T")[0], "%Y-%m-%d"),
                editor=request.user,
                unit=taking_unit,
                strength=strength,
                dosage=dose,
                reminder=reminder,
                clinic_scheduled=False,
                frequency=models.TakingFrequency.objects.get(name=frequency)
            )
            # taking = utils.TakingSchemaScheduled(
            #     timepoint=timepoint,
            #     taking_time=time,
            #     start_date=datetime.strptime(start_date.split("T")[0], "%Y-%m-%d"),
            #     editor=request.user,
            #     unit=taking_unit,
            #     strength=strength,
            #     dosage=dose,
            #     reminder=reminder,
            #     clinic_scheduled=False,
            #     frequency=models.TakingFrequency.objects.get(name=frequency)
            # )
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
        
        serializer = self.serializer_class(models.ScheduledTaking.objects.annotate(prescr_id=
                    F('takingschema__prescriptionschema__prescription')
                ).get(pk=taking.pk))
        # item_dict = {
        #     "pk": taking.pk,
        #     "medicationId": prescr.pk,
        #     "strength": taking.strength,
        #     "dosage": taking.dosage,
        #     "unit": taking.unit.name,
        #     "startTime": force_text(taking.start_date),
        #     "frequency": taking.frequency.name,
        #     "clinic_scheduled": taking.clinic_scheduled,
        #     "reminder": taking.reminder,

        # }

        # if taking.timepoint.name == "custom":
        #     item_dict["schedule"] = {
        #         "type": "custom",
        #         "time": force_text(taking.taking_time)
        #     }
        # else:
        #     item_dict["schedule"] = {
        #         "type": "solar",
        #         "time": taking.timepoint.name,
        #         "actual": force_text(taking.taking_time)
        #     }
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserPreferenceConfigAPIView(APIView):
    authentication_classes = [KiolaAuthentication,]
    render_classes = [JSONRenderer,]

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
        config_data = {
            "data": data.values()
        }
        return Response(config_data, status=status.HTTP_200_OK) 

    @requires_api_login
    def post(self, request, *args, **kwargs):
        try:
            subject = senses.Subject.objects.get(login=request.user)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        
        data = request.data
        med_pref_data = data.get('data', None)
        config_data = {}
        for item in med_pref_data:
            config_data[f'{const.USER_PREFERENCE_CONFIG_PREFIX}{item["type"]}'] = item
        result = models.UserPreferenceConfig.objects.set_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, config_data, request.user)
        return Response({"msg": "Success"}, status=status.HTTP_200_OK)

    @requires_api_login
    def put(self, request, *args, **kwargs):
        try:
            subject = senses.Subject.objects.get(login=request.user)
        except senses.Subject.DoesNotExist:
            raise exceptions.Forbidden("Unknown subject")
        
        data = request.data
        med_pref_data = data.get('data', None)
        config_data = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, request.user)
        for item in med_pref_data:
            config_data[f'{const.USER_PREFERENCE_CONFIG_PREFIX}{item["type"]}'] = item
        result = models.UserPreferenceConfig.objects.set_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, config_data, request.user)
        return Response({"msg": "Success"}, status=status.HTTP_200_OK)

class CompoundSearchAPIView(APIView, PaginationHandlerMixin):

    pagination_class = BasicPagination
    serializer_class = tcc_serializers.CompoundSerializer
    authentication_classes = [KiolaAuthentication,]
    @requires_api_login
    def get(self, request, subject_uid=None, *args, **kwargs):
        
        query = request.GET

        # qs = Compound.objects.all()

#         page = self.paginate_queryset(qs)

#         if page is not None:
#             serializer = self.get_paginated_response(self.serializer_class(page,
#  many=True).data)

#         else:
#             serializer = self.serializer_class(qs, many=True)
        return Response(status=status.HTTP_200_OK)
