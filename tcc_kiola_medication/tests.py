import json
import os
from datetime import datetime
from typing import Tuple

import pytz
from diplomat.models import ISOCountry, ISOLanguage
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone
from django_cron import CronJobManager
from freezegun import freeze_time
from reversion import revisions as reversion
from tcc_kiola_notification import models as notif_models

from kiola.cares.const import USER_GROUP__COORDINATORS
from kiola.kiola_med import models as med_models
from kiola.kiola_pharmacy import models as pharmacy_models
from kiola.kiola_senses import const as senses_const
from kiola.kiola_senses.models import Status, Subject, SubjectStatus
from kiola.kiola_senses.models_devices import (
    Device,
    Device2User,
    DeviceSpecificSensorSetting,
    SensorCategory,
)
from kiola.kiola_senses.tests import KiolaTest
from kiola.utils.commons import get_system_user
from kiola.utils.pyxtures import ProjectPyxtureLoader, PyxtureLoader, SimpleAppConfig
from kiola.utils.tests import KiolaBaseTest, KiolaTestClient, do_request

from . import const, cron, models, utils

# Create your tests here.
from .forms import CompoundImportHistoryForm, ScheduleTakingForm


def get_app_configs(exclude=None):
    app_configs = apps.get_app_configs()
    if exclude:
        is_included = lambda app: app.name not in exclude
        app_configs = filter(is_included, app_configs)
    return list(app_configs)


class MedicationTest(KiolaTest):
    @classmethod
    def setUpClass(cls):
        super(MedicationTest, cls).setUpClass()

        with reversion.create_revision():
            reversion.set_user(get_system_user())
            try:
                ProjectPyxtureLoader().load(
                    app_configs=get_app_configs(exclude=["relief.services"])
                )
            except Exception as err:
                try:
                    del apps.app_configs["services"]
                except Exception as err:
                    pass

                apps_list = apps.get_app_configs()
                ProjectPyxtureLoader().load(apps=apps_list)
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, "datafiles/test/mos_rx_300_rows.csv")
        with reversion.create_revision():
            reversion.set_user(get_system_user())
            with open(file_path, "rb") as fp:
                form = CompoundImportHistoryForm(
                    data={
                        "data_source_description": "test",
                        "data_source_version": "test",
                    },
                    files={
                        "source_file": SimpleUploadedFile(
                            "mos_rx_1000_rows.csv", fp.read()
                        )
                    },
                )
                form.is_valid()
                form.save()

            from tcc_kiola_medication import const, models

            from kiola.kiola_med import models as med_models

            med_models.TakingTimepoint.objects.get_or_create(
                name=const.TAKING_TIMEPOINT__CUSTOM
            )
            med_models.TakingTimepoint.objects.get_or_create(
                name=const.TAKING_TIMEPOINT__AFTERNOON
            )

            models.TakingFrequency.objects.get_or_create(
                name=const.TAKING_FREQUENCY_VALUE__ONCE
            )
            models.TakingFrequency.objects.get_or_create(
                name=const.TAKING_FREQUENCY_VALUE__DAILY
            )
            models.TakingFrequency.objects.get_or_create(
                name=const.TAKING_FREQUENCY_VALUE__WEEKLY
            )
            models.TakingFrequency.objects.get_or_create(
                name=const.TAKING_FREQUENCY_VALUE__FORTNIGHTLY
            )
            models.TakingFrequency.objects.get_or_create(
                name=const.TAKING_FREQUENCY_VALUE__MONTHLY
            )

            models.AdverseReactionType.objects.get_or_create(
                name=const.ADVERSE_REACTION_TYPE__ALLERGY
            )
            models.AdverseReactionType.objects.get_or_create(
                name=const.ADVERSE_REACTION_TYPE__IDIOSYNCRATIC
            )
            models.AdverseReactionType.objects.get_or_create(
                name=const.ADVERSE_REACTION_TYPE__INTOLERANCE
            )
            models.AdverseReactionType.objects.get_or_create(
                name=const.ADVERSE_REACTION_TYPE__SIDE_EFFECT
            )
            models.AdverseReactionType.objects.get_or_create(
                name=const.ADVERSE_REACTION_TYPE__UNKNOWN
            )
            if utils.check_django_version():
                params = dict(
                    defaults={
                        "language": "en",
                        "country": "AU",
                    },
                )
            else:
                params = dict(
                    language=ISOLanguage.objects.get(alpha2="en"),
                    country=ISOCountry.objects.get(alpha2="AU"),
                )

            source, created = med_models.CompoundSource.objects.get_or_create(
                name=const.COMPOUND_SOURCE_NAME__TCC,
                version=const.COMPOUND_SOURCE_VERSION__PATIENT,
                description=const.COMPOUND_SOURCE_DESCRIPTION__PATIENT_ENTERED,
                group="TCC",
                default=False,
                **params,
            )

    def setUp(self):
        super().setUp()
        with reversion.create_revision():
            reversion.set_user(get_system_user())
            self.user = self.create_user(
                username="coordinator",
                group=USER_GROUP__COORDINATORS,
                is_superuser=False,
                email="test@test.test",
                password="12345",
            )

            category = SensorCategory.objects.create(name="Test devices")
            self.device = Device.objects.create(name="Test device", category=category)
            Device.objects.create(name="Typewriter", category=category)
            self.subject = Subject.objects.register(
                username="test_patient", groups=[Group.objects.get(name="Users")]
            )
            Device2User.objects.create(user=self.subject.login, device=self.device)
            # subject status
            status, _ = Status.objects.get_or_create(
                name=senses_const.SUBJECT_STATUS__ACTIVE,
                defaults={"level": senses_const.SUBJECT_STATUS_LEVEL__ACTIVE},
            )
            _, created = SubjectStatus.objects.get_or_create(
                subject=self.subject, status=status
            )

    def clientLogin(self):
        client = self.client_class()
        loginResult = client.login(username="coordinator", password="12345")
        return client

    def test_compound_import(self):
        compound_source_exist = (
            med_models.CompoundSource.objects.filter(
                name=const.COMPOUND_SOURCE_NAME__TCC, version="test"
            ).count()
            == 1
        )
        self.assertTrue(compound_source_exist)
        compound_exist = (
            med_models.Compound.objects.filter(
                uid="342225332", source__version="test"
            ).count()
            == 1
        )
        self.assertTrue(compound_exist)
        product_exist = (
            pharmacy_models.Product.objects.filter(unique_id="342225332").count() == 1
        )
        unit_exist = med_models.TakingUnit.objects.filter(name="Solution").count() == 1
        self.assertTrue(unit_exist)
        prn_exist = (
            models.CompoundExtraInformation.objects.filter(
                compound__uid="342225332",
                name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE,
            ).count()
            == 1
        )
        self.assertTrue(prn_exist)

    def prepare_device(self, url, method):
        remote_access_id, signature, senddate = Device.objects.get_signature(
            url, method, self.device, self.subject.login
        )

    def test_compound_api(self):
        c = self.client

        # test query all
        url = reverse("tcc_med_api:compound", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEquals(response.status_code, 200)
        self.assertEqual(content["next"], (f"{signature_url}?page=2"))
        self.assertEqual(content["previous"], None)
        self.assertEqual(type(content["results"]), list)
        self.assertEqual(len(content["results"]), 80)
        self.assertEqual(content["count"], 116)

        # test query page and limit
        url = reverse("tcc_med_api:compound", kwargs={"apiv": 1})
        url += "?limit=10&page=2"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content["results"]), 10)
        self.assertEqual(
            content["next"],
            (
                f'http://testserver{reverse("tcc_med_api:compound", kwargs={"apiv":1})}?limit=10&page=3'
            ),
        )
        self.assertEqual(
            content["previous"],
            (
                f'http://testserver{reverse("tcc_med_api:compound", kwargs={"apiv":1})}?limit=10'
            ),
        )

        # test query search
        url = reverse("tcc_med_api:compound", kwargs={"apiv": 1})
        url += "?compound=aba"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content["results"]), 5)
        self.assertEqual(content["next"], None)
        self.assertEqual(content["previous"], None)

        url = reverse("tcc_med_api:compound", kwargs={"apiv": 1})
        url += "?active_components=abacavir"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content["results"]), 8)
        self.assertEqual(content["next"], None)
        self.assertEqual(content["previous"], None)

        # test single compound
        url = reverse(
            "tcc_med_api:single-compound", kwargs={"apiv": 1, "id": "342225332"}
        )
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        data = {
            "id": "342225332",
            "name": "abacavir 20 mg/mL oral solution",
            "source": "TCC Kiola Medication (test)",
            "activeComponents": ["abacavir"],
            "medicationType": "PRN",
            "formulation": "Solution",
        }
        self.assertEqual(content, data)

        # test compound create
        param = {
            "name": "brandmew12",
            "activeComponents": ["acName"],
            "medicationType": "PRN",
            "formulation": "Tablet",
        }
        url = reverse("tcc_med_api:compound", kwargs={"apiv": 1})
        url += "?active_components=abacavir"
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        del content["id"]
        data = {
            "name": "brandmew12",
            "source": "TCC Kiola Medication (patient)",
            "activeComponents": ["acName"],
            "medicationType": "PRN",
            "formulation": "Tablet",
        }
        self.assertEqual(content, data)

    def test_prescription_api(self):
        c = self.client

        # test create single
        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {
            "compound": {"id": "342225332"},
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Solution",
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        del content["startDate"]
        del content["endDate"]
        data = {
            "id": "1",
            "reason": "test reason",
            "hint": "Allergy 123",
            "compound": {
                "id": "342225332",
                "name": "abacavir 20 mg/mL oral solution",
                "activeComponents": ["abacavir"],
            },
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Solution",
            "schedule": [],
            "medicationType": "PRN",
            "active": True,
        }
        self.assertEqual(content, data)
        # # test if compound created
        # compound_exist = med_models.Compound.objects.filter(uid="342225332", source__version="test").count() == 1
        # self.assertTrue(compound_exist)
        # prn_exist = models.CompoundExtraInformation.objects.filter(compound__uid="342225332", name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE).count() == 1
        # self.assertTrue(prn_exist)

        # test update single
        url = reverse("tcc_med_api:single-medication", kwargs={"apiv": 1, "id": "1"})
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {
            "compound": {"id": "342225332"},
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Solution",
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason 1",
            "hint": "Allergy 123",
            "medicationType": "PRN",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        del content["startDate"]
        del content["endDate"]
        data = {
            "id": "1",
            "reason": "test reason 1",
            "hint": "Allergy 123",
            "compound": {
                "id": "342225332",
                "name": "abacavir 20 mg/mL oral solution",
                "activeComponents": ["abacavir"],
            },
            "formulation": "Solution",
            "medicationDosage": "200",
            "strength": "30 mg",
            "schedule": [],
            "medicationType": "PRN",
            "active": True,
        }
        self.assertEqual(content, data)

        # test update single with wrong compound id
        param = {
            "compound": {"id": "342283573"},
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Solution",
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        self.assertEquals(response.status_code, 400)

        # test update single without require data
        param = {
            "compound": {"id": "342225332"},
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        self.assertEquals(response.status_code, 400)

        # test query single
        url = reverse("tcc_med_api:single-medication", kwargs={"apiv": 1, "id": "1"})
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        del content["startDate"]
        del content["endDate"]
        data = {
            "id": "1",
            "reason": "test reason 1",
            "hint": "Allergy 123",
            "compound": {
                "id": "342225332",
                "name": "abacavir 20 mg/mL oral solution",
                "activeComponents": ["abacavir"],
            },
            "formulation": "Solution",
            "schedule": [],
            "medicationDosage": "200",
            "strength": "30 mg",
            "medicationType": "PRN",
            "active": True,
        }
        self.assertEqual(content, data)

        # test query all
        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {
            "compound": {"id": "642059707"},
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Solution",
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content["results"]), 2)

        # test change history
        url = reverse("tcc_med_api:medication-history", kwargs={"apiv": 1, "id": "1"})
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        del content["results"][0]["time"]
        data = [
            {
                "changes": [
                    {"field": "reason", "old": "test reason", "new": "test reason 1"}
                ]
            }
        ]
        self.assertEqual(content["results"], data)

        # test delete
        url = reverse("tcc_med_api:single-medication", kwargs={"apiv": 1, "id": "1"})
        signature_url = f"http://testserver{url}"
        method = "DELETE"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        url += "?active=true"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 1)

        url = reverse("tcc_med_api:single-medication", kwargs={"apiv": 1, "id": "2"})
        signature_url = f"http://testserver{url}"
        method = "DELETE"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        url += "?active=true"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {}
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content["results"]), 0)

    def test_taking_api(self):
        self.assertTrue(True)
        c = self.client
        # prepare prescription
        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {
            "compound": {"id": "342225332"},
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Solution",
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # test create single
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        data = {
            "id": "1",
            "medicationId": "1",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "strength": "200mg",
            "dosage": "2",
            "formulation": "Tablet",
            "frequency": "daily",
            "reminder": False,
            "modality": "patient",
            "hint": "hint",
            "time": "18:29:00",
            "type": "custom",
            "active": True,
        }

        content = json.loads(response.content.decode("utf-8"))
        del content["createdAt"]
        del content["updatedAt"]
        self.assertEqual(content, data)
        # test update single
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "solar",
            "time": "noon",
        }
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv": 1, "id": "1"})
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        data = {
            "id": "1",
            "medicationId": "1",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "strength": "200mg",
            "dosage": "2",
            "formulation": "Tablet",
            "frequency": "daily",
            "reminder": False,
            "modality": "patient",
            "hint": "hint",
            "time": "noon",
            "type": "solar",
            "actualTime": "12:00:00",
            "active": True,
        }
        content = json.loads(response.content.decode("utf-8"))

        del content["createdAt"]
        del content["updatedAt"]
        self.assertEqual(content, data)
        # test 400
        # test update single with wrong medication id
        param = {
            "medicationId": "2",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "solar",
            "time": "noon",
        }
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv": 1, "id": "1"})
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        self.assertEquals(response.status_code, 400)
        # test update single without require data
        param = {
            "medicationId": "1",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "solar",
            "time": "noon",
        }
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv": 1, "id": "1"})
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        self.assertEquals(response.status_code, 400)

        # test query single
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv": 1, "id": "1"})
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        data = {
            "id": "1",
            "medicationId": "1",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "strength": "200mg",
            "dosage": "2",
            "formulation": "Tablet",
            "frequency": "daily",
            "reminder": False,
            "modality": "patient",
            "hint": "hint",
            "time": "noon",
            "type": "solar",
            "actualTime": "12:00:00",
            "active": True,
        }
        content = json.loads(response.content.decode("utf-8"))
        del content["createdAt"]
        del content["updatedAt"]
        self.assertEqual(content, data)
        # test query all
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content["results"]), 2)

        # test delete
        param = {}
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv": 1, "id": "1"})
        signature_url = f"http://testserver{url}"
        method = "DELETE"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?active=true"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 1)

        param = {}
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv": 1, "id": "2"})
        signature_url = f"http://testserver{url}"
        method = "DELETE"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?active=true"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 0)

    def test_taking_query_api(self):
        self.assertTrue(True)
        c = self.client
        # prepare prescription
        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {
            "compound": {"id": "342225332"},
            "startDate": "2020-01-01",
            "endDate": "2022-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Capsole",
            "medicationType": "Regular",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # create test schedules
        # daily
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        # weekly 1
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "weekly",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        # weekly 2
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-20",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "weekly",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        # fortnightly 1
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-13",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "fortnightly",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # fortnightly 2
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-20",
            "endDate": "2021-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "fortnightly",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # monthly
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-14",
            "endDate": "2021-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "monthly",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # once
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-05",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "once",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # test startDate
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?startDate=2020-11-10"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 6)

        # test endDate
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?endDate=2020-12-10"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 5)

        # test startDate and endDate
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?startDate=2020-11-10&endDate=2020-12-10"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 4)

        # test givenDate with once
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-05"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 1)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-06"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 0)

        # test givenDate with daily
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-11"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 0)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-12"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 2)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-15"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 1)

        # test givenDate with weekly
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-12"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 2)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-15"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 1)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-19"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 2)

        # test givenDate with fortnightly
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-13"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 2)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-20"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 3)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-27"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 0)

        # test givenDate with monthly
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-11-14"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 2)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2020-12-14"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 1)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2021-01-13"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 1)

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2021-02-12"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 2)

        # test givenDate with endDate:null
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2021-04-12",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        url += "?date=2021-08-12"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 1)

    def test_reaction_api(self):
        c = self.client
        # prepare prescription
        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {
            "compound": {"id": "342225332"},
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Solution",
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # test create single
        param = {
            "compound": {"id": "342225332"},
            "reactionType": "Allergy",
            "reactions": "test reactions",
        }
        url = reverse("tcc_med_api:med_adverse_reaction", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        data = {
            "compound": {"id": "342225332", "name": "abacavir 20 mg/mL oral solution"},
            "reactionType": "Allergy",
            "reactions": "test reactions",
            "active": True,
        }

        content = json.loads(response.content.decode("utf-8"))
        uid = content["id"]
        del content["id"]
        del content["createdAt"]
        del content["updatedAt"]
        self.assertEqual(content, data)
        # test update single
        param = {
            "compound": {"id": "342225332"},
            "reactionType": "Allergy",
            "reactions": "test reactions 11",
        }
        url = reverse(
            "tcc_med_api:single-med_adverse_reaction", kwargs={"apiv": 1, "id": uid}
        )
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        data = {
            "id": uid,
            "compound": {"id": "342225332", "name": "abacavir 20 mg/mL oral solution"},
            "reactionType": "Allergy",
            "reactions": "test reactions 11",
            "active": True,
        }

        content = json.loads(response.content.decode("utf-8"))
        del content["createdAt"]
        del content["updatedAt"]
        self.assertEqual(content, data)

        # test 400 with invalid data
        param = {
            "compound": {"id": "342225332"},
            "reactionType": "Allergy 111",
            "reactions": "test reactions",
        }
        url = reverse(
            "tcc_med_api:single-med_adverse_reaction", kwargs={"apiv": 1, "id": uid}
        )
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        self.assertEquals(response.status_code, 400)

        # test 400 without required data
        param = {"reactionType": "Allergy", "reactions": "test reactions"}
        url = reverse(
            "tcc_med_api:single-med_adverse_reaction", kwargs={"apiv": 1, "id": uid}
        )
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        self.assertEquals(response.status_code, 400)

        # test query single
        url = reverse(
            "tcc_med_api:single-med_adverse_reaction", kwargs={"apiv": 1, "id": uid}
        )
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        data = {
            "id": uid,
            "compound": {"id": "342225332", "name": "abacavir 20 mg/mL oral solution"},
            "reactionType": "Allergy",
            "reactions": "test reactions 11",
            "active": True,
        }

        content = json.loads(response.content.decode("utf-8"))
        del content["createdAt"]
        del content["updatedAt"]
        self.assertEqual(content, data)

        # test query all
        param = {
            "compound": {"id": "342225332"},
            "reactionType": "Allergy",
            "reactions": "test reactions 2",
        }
        url = reverse("tcc_med_api:med_adverse_reaction", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        uid2 = content["id"]

        url = reverse("tcc_med_api:med_adverse_reaction", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content["results"]), 2)
        # test delete
        param = {}
        url = reverse(
            "tcc_med_api:single-med_adverse_reaction", kwargs={"apiv": 1, "id": uid2}
        )
        signature_url = f"http://testserver{url}"
        method = "DELETE"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:med_adverse_reaction", kwargs={"apiv": 1})
        url += "?active=true"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 1)

        param = {}
        url = reverse(
            "tcc_med_api:single-med_adverse_reaction", kwargs={"apiv": 1, "id": uid}
        )
        signature_url = f"http://testserver{url}"
        method = "DELETE"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:med_adverse_reaction", kwargs={"apiv": 1})
        url += "?active=true"
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["count"], 0)

    def test_user_preference_api(self):
        c = self.client
        # test get
        url = reverse("tcc_med_api:user_preference_config", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param={},
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        data = [
            {"type": "morning", "actualTime": "08:00"},
            {"type": "noon", "actualTime": "12:00"},
            {"type": "afternoon", "actualTime": "18:00"},
            {"type": "night", "actualTime": "22:00"},
        ]
        self.assertEqual(content["results"], data)

        # test put
        param = [
            {"type": "morning", "actualTime": "11:00"},
            {"type": "afternoon", "actualTime": "12:00"},
        ]
        url = reverse("tcc_med_api:user_preference_config", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        data = [
            {"type": "morning", "actualTime": "11:00"},
            {"type": "noon", "actualTime": "12:00"},
            {"type": "afternoon", "actualTime": "12:00"},
            {"type": "night", "actualTime": "22:00"},
        ]
        self.assertEqual(content, data)
        # test put with wrong type
        param = [
            {"type": "fornight", "actualTime": "11:00"},
            {"type": "afternoon", "actualTime": "12:00"},
        ]
        url = reverse("tcc_med_api:user_preference_config", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEquals(response.status_code, 400)

        # test put with duplicate type
        param = [
            {"type": "fornight", "actualTime": "11:00"},
            {"type": "fornight", "actualTime": "12:00"},
        ]
        url = reverse("tcc_med_api:user_preference_config", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEquals(response.status_code, 400)

        # test put with invalid time
        param = [
            {"type": "fornight", "actualTime": "11:00"},
            {"type": "afternoon", "actualTime": "12:00 pm"},
        ]
        url = reverse("tcc_med_api:user_preference_config", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        content = json.loads(response.content.decode("utf-8"))
        self.assertEquals(response.status_code, 400)

    def test_medication_reminder(self):
        c = self.client
        # prepare prescription
        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {
            "compound": {"id": "342225332"},
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Solution",
            "startDate": "2020-01-01",
            "endDate": "2022-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        url = reverse("tcc_med_api:medication", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        param = {
            "compound": {"id": "342283573"},
            "medicationDosage": "200",
            "strength": "30 mg",
            "formulation": "Solution",
            "startDate": "2020-01-01",
            "endDate": "2022-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        # create test schedules
        # daily
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-10",
            "endDate": "2020-11-22",
            "reminder": True,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        # weekly 1
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": True,
            "formulation": "Tablet",
            "frequency": "weekly",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        # weekly 2
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-20",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "weekly",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # once
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-05",
            "endDate": "2020-11-22",
            "reminder": True,
            "formulation": "Tablet",
            "frequency": "once",
            "hint": "hint",
            "type": "custom",
            "time": "18:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )
        import dateutil.parser

        # test once
        time_now = dateutil.parser.parse("2020-11-05T18:30:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            # test reminder not generated becaused it is not 10 mins after due
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)  # reminder message

        time_now = dateutil.parser.parse("2020-11-05T18:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            # test reminder is generated
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 1)

        time_now = dateutil.parser.parse("2020-11-05T18:45:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            # test reminder should not be generated twice
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)

        # test daily
        time_now = dateutil.parser.parse("2020-11-11T18:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 1)

        # test weekly
        time_now = dateutil.parser.parse("2020-11-15T18:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 1)

        time_now = dateutil.parser.parse("2020-11-19T18:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 1)

        time_now = dateutil.parser.parse("2020-11-20T18:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 1)

        # fortnightly 1
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-13",
            "endDate": "2020-11-30",
            "reminder": True,
            "formulation": "Tablet",
            "frequency": "fortnightly",
            "hint": "hint",
            "type": "custom",
            "time": "19:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # fortnightly 2
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-20",
            "endDate": "2021-11-30",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "fortnightly",
            "hint": "hint",
            "type": "custom",
            "time": "19:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # test fortnightly
        time_now = dateutil.parser.parse("2020-11-13T19:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 3)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 4)

        time_now = dateutil.parser.parse("2020-11-20T19:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)

        time_now = dateutil.parser.parse("2020-11-27T19:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 1)

        # monthly
        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-11-24",
            "endDate": "2020-12-29",
            "reminder": True,
            "formulation": "Tablet",
            "frequency": "monthly",
            "hint": "hint",
            "type": "custom",
            "time": "21:29",
        }
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-12-10",
            "endDate": "2021-01-02",
            "reminder": True,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "time": "21:29",
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        param = {
            "medicationId": "2",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2020-12-10",
            "endDate": "2021-01-02",
            "reminder": True,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "time": "21:29",
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        # test monthly
        time_now = dateutil.parser.parse("2020-11-24T21:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 1)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 2)

        time_now = dateutil.parser.parse("2020-12-24T21:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            # same med same time will only generate 1 messages
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 2)

        time_now = dateutil.parser.parse("2021-01-23T21:40:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)

        # test solar

        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2021-01-10",
            "endDate": "2021-01-22",
            "reminder": True,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "solar",
            "time": "noon",
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        param = {
            "medicationId": "1",
            "strength": "200mg",
            "dosage": "2",
            "startDate": "2021-01-10",
            "endDate": "2021-01-22",
            "reminder": True,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "solar",
            "time": "afternoon",
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv": 1})
        signature_url = f"http://testserver{url}"
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(
            signature_url, method, self.device, self.subject.login
        )
        response = do_request(
            c,
            method,
            url,
            remote_access_id,
            signature,
            senddate,
            param=param,
            content_type="application/json",
            accept_language=None,
            accept="application/json",
        )

        time_now = dateutil.parser.parse("2021-01-11T12:11:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 1)

        time_now = dateutil.parser.parse("2021-01-11T18:11:00+11:00")
        with freeze_time(time_now):
            time_now = timezone.now()
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 0)
            with CronJobManager(
                cron.ScheduleTakingReminderJob, silent=False
            ) as manager:
                cmd_res = manager.run(True)
            items = notif_models.NotificationItem.objects.filter(
                created__gte=time_now
            ).count()
            self.assertEqual(items, 1)
