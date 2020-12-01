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
    url(r'adverse_reaction/$', views.AdverseReactionAPIView.as_view(), name="adverse_reaction"),
    url(r'adverse_reaction/(?P<pk>\d+)/$', views.AdverseReactionAPIView.as_view(), name="signle-adverse_reaction"),
    # url(r"observation_profile/", views.MedObservationProfileAPIView.as_view(), name='obs_profiles'),

    url(r"compound/$", views.CompoundAPIView.as_view(), name='compound'),
    url(r"compound/(?P<pk>\d+)/$", views.CompoundAPIView.as_view(), name='single-compound'),
    url(r"compound/search/$", views.CompoundSearchAPIView.as_view(), name='compound_search'),

    # url(r"prescriptions/$", views.PrescriptionAPIView.as_view(), name="prescriptions-add"),
    # url(r"prescriptions/(?P<pk>\d+)/$", views.PrescriptionAPIView.as_view(), name="prescriptions-update"),
    url(r"prescription/$", views.PrescriptionAPIView.as_view(), name="prescription"),
    url(r"prescription/(?P<pk>\d+)/$", views.PrescriptionAPIView.as_view(), name="single-prescription"),
    url(r"prescription/(?P<pk>\d+)/history/$", views.PrescriptionHistoryAPIView.as_view(), name="prescription-history"),

    url(r"user_preference_config/$", views.UserPreferenceConfigAPIView.as_view(), name="user_preference_config"),
    url(r"scheduleitem/$", views.TakingSchemaAPIView.as_view(), name="taking"),
    url(r"scheduleitem/(?P<pk>\d+)/$", views.TakingSchemaAPIView.as_view(), name="single-taking"),
    url(r"medreaction/$", views.MedicationAdverseReactionAPIView.as_view(), name="med_adverse_reaction"),
    url(r"medreaction/(?P<pk>\d+)/$", views.MedicationAdverseReactionAPIView.as_view(), name="single-med_adverse_reaction"),
]

