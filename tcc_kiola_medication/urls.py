# -*- coding: utf-8 -*-
# import importlib


# from healthy_heart import 
from django.conf import settings 
from django.conf.urls import include, url


from . import views

from .views import CompoundAPIView, CompoundRudView,  PrescriptionRudView, MedObservationProfileAPIView

urlpatterns = [
    
    url(r"^$", views.index, name='index'),
    # url(r"upload-csv-old/", views.medication_upload_old, name="medication_upload"),
    url(r"upload-csv/", views.medication_upload, name="medication_upload"),
    url(r"prescriptions/", views.prescriptions.as_view()),
    #url(r"compounds/", views.CompoundViewSet),
    url(r"compoundSource/", views.addCompoundSource),

    url(r"allCompounds/", CompoundAPIView.as_view(), name='post-listcreate'),
    url(r"med_obs_profiles/", MedObservationProfileAPIView.as_view(), name='med_obs_profiles'),

    url(r'singleCompound/(?P<pk>\d+)/$', CompoundRudView.as_view(), name='post-rud'),


    #url(r"compoundAPI/(?P<pk>\d+)/", CompoundRudView.as_view(), name='post-rud'),
    #url(r'v(?P<apiv>1)/subjects/(?P<subject_uid>[a-zA-Z0-9\-_]*)/observations/$', views.ObservationResource.as_view(), name="observation"),
    
    # url(r"allPrescriptions/", PrescriptionAPIView.as_view(), name='post-listcreater'),
    url(r'prescription/(?P<subject_id>\d+)/$', PrescriptionRudView.as_view(), name='post-rud'),

      
    ## url(r'api/v(?P<apiv>[0-9\.]+)/', include('kiola.kiola_admin.api_urls', namespace="admin_api")),


    #TODO:
    #Adverse reactions API - don't have the data/where is it?

    #MEDS TESTING:
    url(r'prescr/$', views.PrescriptionListView.as_view(), name="prescription_list"),

    url(r'listPrescriptions/$', views.PrescriptionListAPI.as_view(), name="prescription_listtwo"),
]

