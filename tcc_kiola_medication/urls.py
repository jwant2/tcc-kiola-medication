# -*- coding: utf-8 -*-
# import importlib


# from healthy_heart import
from django.conf import settings
from django.conf.urls import include, url

from kiola.utils.authorization import permission_required_annotated

from . import views

urlpatterns = [
    url(
        r"^m/p/(?P<sid>[a-zA-Z2-9]{21,23})/prescr/$",
        permission_required_annotated(perm="kiola_med.view_index")(
            views.TCCPrescriptionListView.as_view()
        ),
        name="prescription_index",
    ),
    url(
        r"^m/p/(?P<sid>[a-zA-Z2-9]{21,23})/prescr/add/$",
        permission_required_annotated(perm="kiola_med.view_index")(
            views.TCCPrescriptionView.as_view()
        ),
        name="prescription_add",
    ),
    url(
        r"^m/p/(?P<sid>[a-zA-Z2-9]{21,23})/prescr/(?P<fid>\d+)/$",
        permission_required_annotated(perm="kiola_med.view_index")(
            views.TCCPrescriptionView.as_view()
        ),
        name="prescription",
    ),
    url(
        r"^m/p/(?P<sid>[a-zA-Z2-9]{21,23})/prescr/(?P<fid>\d+)/schedule/$",
        permission_required_annotated(perm="kiola_med.view_index")(
            views.TakingSchemaResource.as_view()
        ),
        name="taking",
    ),
    url(
        r"^m/p/(?P<sid>[a-zA-Z2-9]{21,23})/prescr/(?P<fid>\d+)/schedule/(?P<id>\d+)/$",
        permission_required_annotated(perm="kiola_med.view_index")(
            views.TakingSchemaResource.as_view()
        ),
        name="taking-id",
    ),
]
