# -*- coding: utf-8 -*-
# import importlib


# from healthy_heart import 
from django.conf import settings 
from django.conf.urls import include, url


from . import views

from .views import CompoundAPIView, CompoundRudView, PrescriptionAPIView, PrescriptionRudView

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
    url(r"med_obs_profiles/", views.MedObservationProfileAPIView.as_view(), name='med_obs_profiles'),

    url(r"compounds/$", CompoundAPIView.as_view(), name='compounds'),
    url(r"compounds/(?P<pk>\d+)/$", CompoundAPIView.as_view(), name='compounds'),
    url(r"compounds/search/$", views.CompoundSearchAPIView.as_view(), name='compound_search'),

    # url(r"prescriptions/$", views.PrescriptionAPIView.as_view(), name="prescriptions-add"),
    # url(r"prescriptions/(?P<pk>\d+)/$", views.PrescriptionAPIView.as_view(), name="prescriptions-update"),
    url(r"prescriptions/$", views.PrescriptionAPIView.as_view(), name="prescriptions"),
    url(r"prescriptions/(?P<pk>\d+)/$", views.PrescriptionAPIView.as_view(), name="prescriptions"),
    url(r"user-pref/$", views.UserPreferenceConfigAPIView.as_view(), name="user-preference"),
    url(r"scheduleitem/$", views.TakingSchemaAPIView.as_view(), name="takings"),
    url(r"scheduleitem/(?P<pk>\d+)/$", views.TakingSchemaAPIView.as_view(), name="takings"),
    url(r"medreaction/$", views.MedicationAdverseReactionAPIView.as_view(), name="med_adverse_reactions"),
    url(r"medreaction/(?P<pk>\d+)/$", views.MedicationAdverseReactionAPIView.as_view(), name="med_adverse_reactions"),
]

