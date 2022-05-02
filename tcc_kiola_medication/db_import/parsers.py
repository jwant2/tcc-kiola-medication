# -*- coding: utf-8 -*-
import csv
import io
import time

from diplomat.models import ISOCountry, ISOLanguage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from reversion import revisions as reversion
from tcc_kiola_medication import const, models

import kiola.kiola_pharmacy.parsers as parsers
from kiola.kiola_med import models as med_models
from kiola.kiola_pharmacy.models import ImportHistory, Product
from kiola.utils import logger
from kiola.utils.commons import get_system_user
from kiola.utils.signals import signal_registry

from .. import utils


class BaseParser(object):
    source_file = None
    version = "1.0"

    def __init__(self, source_file, version):
        self.source_file = source_file
        self.version = version
        self.error_logs = []

    def parse(self):
        raise AttributeError("Call to abstract method.")


class TCCMosParser(BaseParser):
    def parse(self):
        with open(self.source_file, "r") as csv_file:
            file_data = csv_file
            data_set = file_data.read()
            io_string = io.StringIO(data_set)
        next(io_string)

        with reversion.create_revision():
            reversion.set_user(get_system_user())
            print("Creating data source ...")
            # create new compound source
            if utils.check_django_version():
                params = dict(
                    defaults={"language": "en", "country": "AU"},
                )
            else:
                params = dict(
                    language=ISOLanguage.objects.get(alpha2="en"),
                    country=ISOCountry.objects.get(alpha2="AU"),
                )

            source, created = med_models.CompoundSource.objects.get_or_create(
                name=const.COMPOUND_SOURCE_NAME__TCC,
                version=self.version,
                group="TCC",
                default=True,
                **params
            )

            formulations = {}
            print("Importing data ...")
            # FIXME: unable to handle any other PBS data format
            # loop csv file data row by row
            counter = 0
            for column in csv.reader(
                io_string, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL
            ):
                try:
                    check_exists = med_models.Compound.objects.filter(
                        name=column[1], uid=column[4], source=source
                    ).count()
                    if check_exists > 0:
                        continue  # skip duplicates
                    # process and create active components data
                    try:
                        ac, created = med_models.ActiveComponent.objects.get_or_create(
                            name=column[0]
                        )
                        if created:
                            ac.name_ref = column[4]
                            ac.save()
                    except:
                        ac = med_models.ActiveComponent.objects.filter(
                            name=column[0]
                        ).first()

                    # process SCH/PRN
                    prn_value = column[32]
                    if prn_value == "Yes":
                        med_type = const.MEDICATION_TYPE_VALUE__REGULAR
                    else:
                        med_type = const.MEDICATION_TYPE_VALUE__PRN

                    dosageform = column[26]
                    dosageform_ref = dosageform[:3].upper()
                    if dosageform == "":
                        dosageform = "N/A"
                        dosageform_ref = "N/A"
                    else:
                        formulations[dosageform] = dosageform_ref
                        # unit, created = med_models.TakingUnit.objects.get_or_create(name=dosageform)
                        # if created:
                        #     unit.descrition=dosageform_ref
                        #     unit.save
                    # create or update medication product data
                    Product.objects.update_or_create(
                        unique_id=column[4],
                        defaults={
                            "title": column[1],
                            "unique_id": column[4],
                            "meta_data": '{"active_components": {"1":"'
                            + column[0]
                            + '"}, "SCH/PRN": "'
                            + prn_value
                            + '", "source": {"name": "'
                            + const.COMPOUND_SOURCE_NAME__TCC
                            + '", "version": "'
                            + self.version
                            + '"}, "dosage_form": {"'
                            + dosageform_ref
                            + '": "'
                            + dosageform
                            + '"}}',
                        },
                    )
                    # create or update compound data
                    compound, created = med_models.Compound.objects.update_or_create(
                        uid=column[4],
                        name=column[1],
                        defaults={
                            "source": source,
                            "name": column[1],
                            "dosage_form": column[26],
                        },
                    )
                    if ac:
                        compound.active_components.add(ac)
                        compound.save()

                    # store PRN data
                    (
                        prn,
                        created,
                    ) = models.CompoundExtraInformation.objects.get_or_create(
                        compound=compound,
                        name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE,
                    )
                    if created:
                        prn.value = med_type
                        prn.save()

                    counter += 1
                except Exception as error:
                    # store error data row and error message in ImportHistory.details
                    error_log = {"error_msg": str(error), "error_data": column}
                    self.error_logs.append(error_log)

            print("Creating taking unit data ...")
            for key in formulations.keys():
                unit, created = med_models.TakingUnit.objects.get_or_create(name=key)
                if created:
                    unit.descrition = formulations[key]
                    unit.save
            print("Finalising import ...")
            return counter, self.error_logs


class TCCMGenericParser(BaseParser):
    def parse(self):
        with open(self.source_file, "r") as csv_file:
            file_data = csv_file
            data_set = file_data.read()
            io_string = io.StringIO(data_set)
        next(io_string)

        with reversion.create_revision():
            reversion.set_user(get_system_user())
            print("Creating data source ...")
            # create new compound source
            if utils.check_django_version():
                params = dict(
                    defaults={"language": "en", "country": "AU"},
                )
            else:
                params = dict(
                    language=ISOLanguage.objects.get(alpha2="en"),
                    country=ISOCountry.objects.get(alpha2="AU"),
                )

            source, created = med_models.CompoundSource.objects.get_or_create(
                name=const.COMPOUND_SOURCE_NAME__TCC,
                version=self.version,
                group="TCC",
                default=True,
                **params
            )

            formulations = {}
            print("Importing data ...")
            # FIXME: unable to handle any other PBS data format
            # loop csv file data row by row
            counter = 0
            for column in csv.reader(
                io_string, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL
            ):
                if column[0] == "":
                    continue  # skip empty line
                uid = column[4]
                name = column[0]
                try:
                    check_exists = med_models.Compound.objects.filter(
                        name=name, source=source
                    ).count()
                    if check_exists > 0:
                        continue  # skip duplicate lines as we only need generic names
                    # process and create active components data
                    try:
                        ac, created = med_models.ActiveComponent.objects.get_or_create(
                            name=column[0]
                        )
                    except:
                        ac = med_models.ActiveComponent.objects.filter(
                            name=name
                        ).first()

                    dosageform = "N/A"
                    dosageform_ref = "N/A"

                    # create or update medication product data
                    Product.objects.update_or_create(
                        unique_id=uid,
                        defaults={
                            "title": name,
                            "unique_id": uid,
                            "meta_data": '{"active_components": {"1":"'
                            + name
                            + '"}, "SCH/PRN": "N/A", "source": {"name": "'
                            + const.COMPOUND_SOURCE_NAME__TCC
                            + '", "version": "'
                            + self.version
                            + '"}, "dosage_form": {"'
                            + dosageform_ref
                            + '": "'
                            + dosageform
                            + '"}}',
                        },
                    )
                    # create or update compound data
                    compound, created = med_models.Compound.objects.update_or_create(
                        uid=uid,
                        name=name,
                        defaults={
                            "uid": uid,
                            "source": source,
                            "name": name,
                            "dosage_form": "N/A",
                        },
                    )
                    if ac:
                        compound.active_components.add(ac)
                        compound.save()

                    counter += 1
                except Exception as error:
                    # store error data row and error message in ImportHistory.details
                    error_log = {"error_msg": str(error), "error_data": column}
                    self.error_logs.append(error_log)

            print("Finalising import ...")
            return counter, self.error_logs


class MedicationDataImportParser(object):
    def new_instance(self, source_type, source_file, version):
        ## check source type and select parser
        return {"TCC": TCCMosParser, "TCC-Generic": TCCMGenericParser,}.get(
            source_type
        )(source_file, version)
