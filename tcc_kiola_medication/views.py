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


from .serializers import CompoundSerializer, CompoundaSerializer, PrescriptionSerializer
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

from kiola.utils import const as kiola_const

#testing meds
from kiola.utils import views as kiola_views
from kiola.kiola_senses import models as senses

from django.db.models import Q, Prefetch
get_for_model = ContentType.objects.get_for_model
from django.template.response import TemplateResponse
from reversion import models as reversion

from kiola.kiola_med import utils

from kiola.utils.commons import get_system_user
from reversion import revisions as reversionrevisions

import dateutil.parser

#pagination:
import rest_framework.pagination
from rest_framework.pagination import PageNumberPagination
from .utils import PaginationHandlerMixin

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
    serializer_class = CompoundSerializer
    # authentication_classes = [KiolaAuthentication,]
    # @requires_api_login
    def get(self, request, subject_uid=None,uid=None, *args, **kwargs):
        
        qs = Compound.objects.all()

        page = self.paginate_queryset(qs)
        # print('count', page.count())
        print('query', len(page))

        if page is not None:
            serializer = self.get_paginated_response(self.serializer_class(page,
 many=True).data)

        else:
            serializer = self.serializer_class(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompoundRudView(generics.RetrieveUpdateDestroyAPIView): # DetailView CreateView FormView
    lookup_field            = 'pk' 
    serializer_class        = CompoundaSerializer

    

    @authentication.requires_api_login
    def get_queryset(self):
        return Compound.objects.all()

    @authentication.requires_api_login
    def get_serializer_context(self, *args, **kwargs):
        return {"request": self.request}


class PrescriptionRudView(generics.RetrieveUpdateDestroyAPIView): # DetailView CreateView FormView
    lookup_field            = 'subject_id' 
    serializer_class        = PrescriptionSerializer

    

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
        
        qs = models.Prescription.objects.select_related('compound', 'status')\
                                        .filter(subject=subject,
                                                status__name=const.PRESCRIPTION_STATUS__ACTIVE)\
                                        .prefetch_related(Prefetch('prescriptionevent_set',
                                                                   queryset=models.PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__PRESCRIBED,
                                                                                                                            const.EVENT_TYPE__END, ])\
                                                                                                            .select_related("etype")\
                                                                                                            .order_by("timepoint")),
                                                          Prefetch('prescriptionevent_set',
                                                                   queryset=models.PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__ADDED, ])\
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
        qs = models.Prescription.objects.select_related('compound', 'status')\
                                        .filter(subject=subject,
                                                status__name=const.PRESCRIPTION_STATUS__INACTIVE)\
                                        .prefetch_related(Prefetch('prescriptionevent_set',
                                                                    queryset=models.PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__ADDED,
                                                                                                                                      const.EVENT_TYPE__CANCELED,
                                                                                                                                      const.EVENT_TYPE__REPLACED])\
                                                                                                      .select_related("etype")\
                                                                                                      .order_by("timepoint")),
                                                          Prefetch('prescriptionevent_set',
                                                                   queryset=models.PrescriptionEvent.objects.filter(etype__name__in=[const.EVENT_TYPE__PRESCRIBED,
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
        pprelation = models.PrescriptionProfileRelation.objects.filter(active=True,
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


