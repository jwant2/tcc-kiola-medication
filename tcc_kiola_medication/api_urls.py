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
]

