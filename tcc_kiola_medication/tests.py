import json
from datetime import datetime
from typing import Tuple
import pytz
import os

from django.test import TestCase
from reversion import revisions as reversion
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import resolve, reverse
from django.contrib.auth.models import User, Group, Permission

from kiola.utils.tests import do_request, KiolaBaseTest
from kiola.kiola_senses.tests import KiolaTest
from kiola.utils.pyxtures import PyxtureLoader, SimpleAppConfig, ProjectPyxtureLoader
from kiola.utils.commons import get_system_user
from kiola.kiola_senses.models import Subject
from kiola.utils.tests import KiolaTestClient
from kiola.kiola_med import models as med_models
from kiola.kiola_pharmacy import models as pharmacy_models
from kiola.cares.const import USER_GROUP__COORDINATORS
from kiola.kiola_senses.models_devices import Device, SensorCategory, Device2User, DeviceSpecificSensorSetting

# Create your tests here.
from .forms import CompoundImportHistoryForm, ScheduleTakingForm
from . import models, const

class MedicationTest(KiolaTest):
    @classmethod
    def setUpClass(cls):
        super(MedicationTest, cls).setUpClass()
        try:
            settings.INSTALLED_APPS.remove("relief.services")
        except Exception as err:
            pass
        ProjectPyxtureLoader().load()
        module_dir = os.path.dirname(__file__)  # get current directory
        file_path = os.path.join(module_dir, 'testfile/mos_rx_1000_rows.csv')
        with reversion.create_revision():
            reversion.set_user(get_system_user())
            with open(file_path, 'rb') as fp:
                form = CompoundImportHistoryForm(
                                                  data={ "data_source_description": "test", "data_source_version": "test"}, 
                                                  files={"source_file": SimpleUploadedFile('mos_rx_1000_rows.csv', fp.read())}
                                                )
                form.is_valid()
                form.save()

            from tcc_kiola_medication import const, models
            from kiola.kiola_med import models as med_models
            med_models.TakingTimepoint.objects.get_or_create(name=const.TAKING_TIMEPOINT__CUSTOM)
            med_models.TakingTimepoint.objects.get_or_create(name=const.TAKING_TIMEPOINT__AFTERNOON)
            
            models.TakingFrequency.objects.get_or_create(name=const.TAKING_FREQUENCY_VALUE__ONCE_ONLY)
            models.TakingFrequency.objects.get_or_create(name=const.TAKING_FREQUENCY_VALUE__DAILY)
            models.TakingFrequency.objects.get_or_create(name=const.TAKING_FREQUENCY_VALUE__WEEKLY)
            models.TakingFrequency.objects.get_or_create(name=const.TAKING_FREQUENCY_VALUE__FORNIGHTLY)
            models.TakingFrequency.objects.get_or_create(name=const.TAKING_FREQUENCY_VALUE__MONTHLY)

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


    def setUp(self):
        super().setUp()
        with reversion.create_revision():
            reversion.set_user(get_system_user())
            self.user = self.create_user(
                username='coordinator',
                group=USER_GROUP__COORDINATORS,
                is_superuser=False,
                email='test@test.test',
                password='12345'
            )

            category = SensorCategory.objects.create(name="Test devices")
            self.device = Device.objects.create(name="Test device", category=category)
            Device.objects.create(name="Typewriter", category=category)
            self.subject = Subject.objects.register(username="test_patient", groups=[Group.objects.get(name="Users")])
            Device2User.objects.create(user=self.subject.login, device=self.device)

    def clientLogin(self):
        client = self.client_class()
        loginResult = client.login(username='coordinator', password='12345')
        return client

    def test_compound_import(self):
        compound_source_exist = med_models.CompoundSource.objects.filter(name=const.COMPOUND_SOURCE_NAME__TCC, version="test").count() == 1
        self.assertTrue(compound_source_exist)
        compound_exist = med_models.Compound.objects.filter(uid="342225332", source__version="test").count() == 1
        self.assertTrue(compound_exist)
        product_exist = pharmacy_models.Product.objects.filter(unique_id="342225332").count() == 1
        unit_exist = med_models.TakingUnit.objects.filter(name="Solution").count()  == 1 
        self.assertTrue(unit_exist)
        prn_exist = models.CompoundExtraInformation.objects.filter(compound__uid="342225332", name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE).count() == 1 
        self.assertTrue(prn_exist)

    def prepare_device(self, url, method):
        remote_access_id, signature, senddate = Device.objects.get_signature(url, method, self.device, self.subject.login)


    def test_compound_api(self):
        c = self.client

        # test query all
        url = reverse("tcc_med_api:compound", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))

        self.assertEquals(response.status_code, 200)
        self.assertEqual(content['next'], (f'{signature_url}?page=2'))
        self.assertEqual(content['previous'], None)
        self.assertEqual(type(content['results']), list)
        self.assertEqual(len(content['results']), 80)
        self.assertEqual(content['count'], 473)
 
        # test query page and limit
        url = reverse("tcc_med_api:compound", kwargs={"apiv":1})
        url += "?limit=10&page=2"
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content['results']), 10)
        self.assertEqual(content['next'], (f'http://testserver{reverse("tcc_med_api:compound", kwargs={"apiv":1})}?limit=10&page=3'))
        self.assertEqual(content['previous'], (f'http://testserver{reverse("tcc_med_api:compound", kwargs={"apiv":1})}?limit=10'))

        # test query search
        url = reverse("tcc_med_api:compound", kwargs={"apiv":1})
        url += "?compound=aba"
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content['results']), 7)
        self.assertEqual(content['next'], None)
        self.assertEqual(content['previous'], None)

        url = reverse("tcc_med_api:compound", kwargs={"apiv":1})
        url += "?active_components=abacavir"
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content['results']), 8)
        self.assertEqual(content['next'], None)
        self.assertEqual(content['previous'], None)

        # test single compound
        url = reverse("tcc_med_api:single-compound", kwargs={"apiv":1, "id":"342225332"})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content), 1)
        data =     {
        "id": "342225332",
        "name": "abacavir 20 mg/mL oral solution",
        "source": "TCC Kiola Medication (test)",
        "activeComponents": [
            "abacavir"
        ],
        "formulation": "Solution"
        }
        self.assertEqual(content[0], data)

    def test_prescription_api(self):
        c = self.client

        # test create single
        url = reverse("tcc_med_api:medication", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
        param = {
            "compound": {
                "id": "342225332"
            },
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN"   
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
            accept="application/json")

        content = json.loads(response.content.decode("utf-8"))
        del content[0]["startDate"]
        del content[0]["endDate"]
        data = [
          {
              "id": "1",
              "reason": "test reason",
              "hint": "Allergy 123",
              "compound": {
                  "id": "342225332",
                  "name": "abacavir 20 mg/mL oral solution",
                  "activeComponents": [
                      "abacavir"
                  ]
              },
              "formulation": "Solution",
              "schedules": [],
              "medicationType": "PRN"
          }
        ]
        self.assertEqual(content, data)

        # test update single
        url = reverse("tcc_med_api:single-medication", kwargs={"apiv":1, "id":"1"})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
        param = {
            "compound": {
                "id": "342225332"
            },
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason 1",
            "hint": "Allergy 123",
            "medicationType": "PRN"   
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
            accept="application/json")

        content = json.loads(response.content.decode("utf-8"))

        del content[0]["startDate"]
        del content[0]["endDate"]
        data = [
          {
              "id": "1",
              "reason": "test reason 1",
              "hint": "Allergy 123",
              "compound": {
                  "id": "342225332",
                  "name": "abacavir 20 mg/mL oral solution",
                  "activeComponents": [
                      "abacavir"
                  ]
              },
              "formulation": "Solution",
              "schedules": [],
              "medicationType": "PRN"
          }
        ]
        self.assertEqual(content, data)

        # test update single with wrong compound id
        param = {
            "compound": {
                "id": "342283573"
            },
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN"   
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
            accept="application/json")
        self.assertEquals(response.status_code, 400)

        # test update single without require data 
        param = {
            "compound": {
                "id": "342225332"
            },
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
            accept="application/json")
        self.assertEquals(response.status_code, 400)

        # test query single
        url = reverse("tcc_med_api:single-medication", kwargs={"apiv":1, "id":"1"})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        content = json.loads(response.content.decode("utf-8"))
        del content[0]["startDate"]
        del content[0]["endDate"]
        data = [
          {
              "id": "1",
              "reason": "test reason 1",
              "hint": "Allergy 123",
              "compound": {
                  "id": "342225332",
                  "name": "abacavir 20 mg/mL oral solution",
                  "activeComponents": [
                      "abacavir"
                  ]
              },
              "formulation": "Solution",
              "schedules": [],
              "medicationType": "PRN"
          }
        ]
        self.assertEqual(content, data)

        # test query all
        url = reverse("tcc_med_api:medication", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
        param = {
            "compound": {
                "id": "642059707"
            },
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN"   
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
            accept="application/json")

        url = reverse("tcc_med_api:medication", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content), 2)

        # test change history
        url = reverse("tcc_med_api:medication-history", kwargs={"apiv":1, "id":"1"})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        del content[0]["time"]
        data = [
            {
                "changes": [
                    {
                        "field": "reason",
                        "old": "test reason",
                        "new": "test reason 1"
                    }
                ]
            }
        ]
        self.assertEqual(content, data)

        # test delete 
        url = reverse("tcc_med_api:single-medication", kwargs={"apiv":1, "id":"1"})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
        param = {
            "compound": {
                "id": "342225332"
            },
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason 1",
            "hint": "Allergy 123",
            "active": False,
            "medicationType": "PRN"   
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
            accept="application/json")


        url = reverse("tcc_med_api:medication", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content), 1)

        url = reverse("tcc_med_api:single-medication", kwargs={"apiv":1, "id":"2"})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
        param = {
            "compound": {
                "id": "642059707"
            },
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "active": False,
            "medicationType": "PRN"   
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
            accept="application/json")

        url = reverse("tcc_med_api:medication", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content), 0)


    def test_taking_api(self):
        self.assertTrue(True)
        c = self.client
        # prepare prescription
        url = reverse("tcc_med_api:medication", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
        param = {
            "compound": {
                "id": "342225332"
            },
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN"   
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
            accept="application/json")

        # test create single
        param = {
            "medicationId": 1,
            "strength": "200mg",
            "dosage": 2,
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "time": "18:29"
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        data = [
              {
                  "id": "2",
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
                  "actualTime": None
              }
          ]
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content, data)
        # test update single
        param = {
            "medicationId": 1,
            "strength": "200mg",
            "dosage": 2,
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "solar",
            "time": "noon"
        }
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv":1,"id":"2"})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        data = [
            {
                "id": "2",
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
                "actualTime": "12:00:00"
            }
        ]
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content, data)
        # test 400
        # test update single with wrong medication id
        param = {
            "medicationId": 2,
            "strength": "200mg",
            "dosage": 2,
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "solar",
            "time": "noon"
        }
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv":1,"id":"2"})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        self.assertEquals(response.status_code, 400)
        # test update single without require data 
        param = {
            "medicationId": 1,
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "solar",
            "time": "noon"
        }
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv":1,"id":"2"})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        self.assertEquals(response.status_code, 400)

        # test query single
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv":1,"id":"2"})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        data = [
            {
                "id": "2",
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
                "actualTime": "12:00:00"
            }
        ]
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content, data)
        # test query all
        param = {
            "medicationId": 1,
            "strength": "200mg",
            "dosage": 2,
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "time": "18:29"
        }
        url = reverse("tcc_med_api:taking", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        url = reverse("tcc_med_api:taking", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content), 2)

        # test delete 
        param = {
            "medicationId": 1,
            "strength": "200mg",
            "dosage": 2,
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "custom",
            "active": False,
            "time": "18:29"
        }
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv":1,"id":"2"})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        url = reverse("tcc_med_api:taking", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content), 1)

        param = {
            "medicationId": 1,
            "strength": "200mg",
            "dosage": 2,
            "startDate": "2020-11-12",
            "endDate": "2020-11-22",
            "reminder": False,
            "formulation": "Tablet",
            "frequency": "daily",
            "hint": "hint",
            "type": "solar",
            "active": False,
            "time": "noon"
        }
        url = reverse("tcc_med_api:single-taking", kwargs={"apiv":1,"id":"3"})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        url = reverse("tcc_med_api:taking", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content), 0)

    def test_reaction_api(self):
        c = self.client
        # prepare prescription
        url = reverse("tcc_med_api:medication", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
        param = {
            "compound": {
                "id": "342225332"
            },
            "startDate": "2020-01-01",
            "endDate": "2020-01-01",
            "reason": "test reason",
            "hint": "Allergy 123",
            "medicationType": "PRN"   
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
            accept="application/json")

        # test create single
        param = {
            "medicationId": "1",
            "reactionType": "Allergy",
            "reactions": "test reactions"
        }
        url = reverse("tcc_med_api:med_adverse_reaction", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        data = [
            {
                "compound": {
                    "id": "342225332",
                    "name": "abacavir 20 mg/mL oral solution"
                },
                "reactionType": "Allergy",
                "reactions": "test reactions",
                "active": True
            }
        ]
        content = json.loads(response.content.decode("utf-8"))
        uid = content[0]["uid"]
        del content[0]["uid"]
        del content[0]["createdAt"]
        del content[0]["updatedAt"]
        self.assertEqual(content, data)
        # test update single
        param = {
            "medicationId": "1",
            "reactionType": "Allergy",
            "reactions": "test reactions 11"
        }
        url = reverse("tcc_med_api:single-med_adverse_reaction", kwargs={"apiv":1, "id":uid})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        data = [
            {
                "uid": uid,
                "compound": {
                    "id": "342225332",
                    "name": "abacavir 20 mg/mL oral solution"
                },
                "reactionType": "Allergy",
                "reactions": "test reactions 11",
                "active": True
            }
        ]
        content = json.loads(response.content.decode("utf-8"))
        del content[0]["createdAt"]
        del content[0]["updatedAt"]
        self.assertEqual(content, data)

        # test 400 with invalid data
        param = {
            "medicationId": "1",
            "reactionType": "Allergy 111",
            "reactions": "test reactions"
        }
        url = reverse("tcc_med_api:single-med_adverse_reaction", kwargs={"apiv":1, "id":uid})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        self.assertEquals(response.status_code, 400)

        # test 400 without required data
        param = {
            "reactionType": "Allergy",
            "reactions": "test reactions"
        }
        url = reverse("tcc_med_api:single-med_adverse_reaction", kwargs={"apiv":1, "id":uid})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        self.assertEquals(response.status_code, 400)


        # test query single
        url = reverse("tcc_med_api:single-med_adverse_reaction", kwargs={"apiv":1, "id":uid})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        data = [
            {
                "uid": uid,
                "compound": {
                    "id": "342225332",
                    "name": "abacavir 20 mg/mL oral solution"
                },
                "reactionType": "Allergy",
                "reactions": "test reactions 11",
                "active": True
            }
        ]
        content = json.loads(response.content.decode("utf-8"))
        del content[0]["createdAt"]
        del content[0]["updatedAt"]
        self.assertEqual(content, data)

        # test query all
        param = {
            "medicationId": "1",
            "reactionType": "Allergy",
            "reactions": "test reactions 2"
        }
        url = reverse("tcc_med_api:med_adverse_reaction", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        uid2 = content[0]["uid"]

        url = reverse("tcc_med_api:med_adverse_reaction", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(len(content), 2)
        # test delete 
        param = {
            "medicationId": "1",
            "reactionType": "Allergy",
            "active": False,
            "reactions": "test reactions 2"
        }
        url = reverse("tcc_med_api:single-med_adverse_reaction", kwargs={"apiv":1, "id":uid2})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        url = reverse("tcc_med_api:single-med_adverse_reaction", kwargs={"apiv":1, "id": uid2})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        data = [
            {
                "uid": uid2,
                "compound": {
                    "id": "342225332",
                    "name": "abacavir 20 mg/mL oral solution"
                },
                "reactionType": "Allergy",
                "reactions": "test reactions 2",
                "active": False
            }
        ]
        content = json.loads(response.content.decode("utf-8"))
        del content[0]["createdAt"]
        del content[0]["updatedAt"]
        self.assertEqual(content, data)


        param = {
            "medicationId": "1",
            "reactionType": "Allergy",
            "active": False,
            "reactions": "test reactions 11"
        }
        url = reverse("tcc_med_api:single-med_adverse_reaction", kwargs={"apiv":1, "id":uid})
        signature_url = f'http://testserver{url}'
        method = "POST"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")

        url = reverse("tcc_med_api:single-med_adverse_reaction", kwargs={"apiv":1, "id":uid})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        data = [
            {
                "uid": uid,
                "compound": {
                    "id": "342225332",
                    "name": "abacavir 20 mg/mL oral solution"
                },
                "reactionType": "Allergy",
                "reactions": "test reactions 11",
                "active": False
            }
        ]
        content = json.loads(response.content.decode("utf-8"))
        del content[0]["createdAt"]
        del content[0]["updatedAt"]
        self.assertEqual(content, data)


    def test_user_preference_api(self):
        c = self.client
        # test get 
        url = reverse("tcc_med_api:user_preference_config", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "GET"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        data = [
            {
                "type": "morning",
                "actualTime": "08:00"
            },
            {
                "type": "noon",
                "actualTime": "12:00"
            },
            {
                "type": "afternoon",
                "actualTime": "18:00"
            },
            {
                "type": "night",
                "actualTime": "22:00"
            }
        ]
        self.assertEqual(content, data)

        # test put
        param = [
            {"type": "morning", "actualTime": "11:00"},
            {"type": "afternoon", "actualTime": "12:00"}
        ]
        url = reverse("tcc_med_api:user_preference_config", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        data = [
            {
                "type": "morning",
                "actualTime": "11:00"
            },
            {
                "type": "noon",
                "actualTime": "12:00"
            },
            {
                "type": "afternoon",
                "actualTime": "12:00"
            },
            {
                "type": "night",
                "actualTime": "22:00"
            }
        ]
        self.assertEqual(content, data)
        # test put with wrong type
        param = [
            {"type": "fornight", "actualTime": "11:00"},
            {"type": "afternoon", "actualTime": "12:00"}
        ]
        url = reverse("tcc_med_api:user_preference_config", kwargs={"apiv":1})
        signature_url = f'http://testserver{url}'
        method = "PUT"
        remote_access_id, signature, senddate = Device.objects.get_signature(signature_url, method, self.device, self.subject.login)
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
            accept="application/json")
        content = json.loads(response.content.decode("utf-8"))
        self.assertEquals(response.status_code, 400)
