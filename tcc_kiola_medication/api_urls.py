# -*- coding: utf-8 -*-
# import importlib


# from healthy_heart import 
from django.conf import settings 
from django.conf.urls import include, url


from . import views


urlpatterns = [
    
    ## medications
    # fetch medications
    # submit medication
    
    ## presciptions
    # fetch prescriptions
    # add prescription
    # update prescription
    # deactivate prescription

    ## Adverse Reactions  -- Notes ?
    # fetch Adverse Reaction
    # submit Adverse Reaction


    #Adverse reactions API - don't have the data/where is it?
    # url(r'adverse_reaction/$', views.AdverseReactionAPIView.as_view(), name="adverse_reaction"),
    # url(r'adverse_reaction/(?P<pk>\d+)/$', views.AdverseReactionAPIView.as_view(), name="signle-adverse_reaction"),
    # url(r"observation_profile/", views.MedObservationProfileAPIView.as_view(), name='obs_profiles'),
    url(r'tcc/$', views.TCCAutocompleteResource.as_view()),
    url(r"compound/$", views.CompoundAPIView.as_view(), name='compound'),
    url(r"compound/(?P<id>[a-zA-Z0-9\-_]*)/$", views.CompoundAPIView.as_view(), name='single-compound'),
    # url(r"compound/search/$", views.CompoundSearchAPIView.as_view(), name='compound_search'),

    # url(r"prescriptions/$", views.PrescriptionAPIView.as_view(), name="prescriptions-add"),
    # url(r"prescriptions/(?P<pk>\d+)/$", views.PrescriptionAPIView.as_view(), name="prescriptions-update"),
    url(r"medication/$", views.PrescriptionAPIView.as_view(), name="medication"),
    url(r"medication/(?P<id>\d+)/$", views.PrescriptionAPIView.as_view(), name="single-medication"),
    url(r"medication/(?P<id>\d+)/history/$", views.PrescriptionHistoryAPIView.as_view(), name="medication-history"),

    url(r"user_preference/$", views.UserPreferenceConfigAPIView.as_view(), name="user_preference_config"),
    url(r"schedule/$", views.TakingSchemaAPIView.as_view(), name="taking"),
    url(r"schedule/(?P<id>\d+)/$", views.TakingSchemaAPIView.as_view(), name="single-taking"),
    url(r"reaction/$", views.MedicationAdverseReactionAPIView.as_view(), name="med_adverse_reaction"),
    url(r"reaction/(?P<id>[a-zA-Z0-9\-_]*)/$", views.MedicationAdverseReactionAPIView.as_view(), name="single-med_adverse_reaction"),
]

