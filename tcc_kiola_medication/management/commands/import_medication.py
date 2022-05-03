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

log = logger.KiolaLogger(__name__).getLogger()
from tcc_kiola_medication.db_import.parsers import MedicationDataImportParser


class Command(BaseCommand):

    help = """Create or update medication database from PBS sources."""

    def add_arguments(self, parser):
        parser.add_argument("source", type=str)
        parser.add_argument("source_type", type=str)
        parser.add_argument("source_version", type=str)
        # parser.add_argument("--no-default",
        #                     action="store_true",
        #                     dest="no_default",
        #                     default=False,
        #                     help="Don't register the import as default source")

    def handle(self, *args, **options):
        log_details = []
        source = options.get("source", None)
        version = options.get("source_version", None)
        source_type = options.get("source_type", None)
        # no_default = options.get("no_default", False)

        print("Checking data source version...")
        exist = (
            med_models.CompoundSource.objects.filter(
                name=const.COMPOUND_SOURCE_NAME__TCC, version=version
            ).count()
            > 0
        )
        if exist:
            msg = f"Given data source version already exist!"
            raise CommandError(msg)

        parser = MedicationDataImportParser().new_instance(source_type, source, version)
        if parser is None:
            raise CommandError("Could not find suitable parser for '%s'" % source_type)
        # mark any "open" imports as failed:
        with transaction.atomic():
            ImportHistory.objects.filter(status="S").update(status="F")
        print("Creating import history record ...")
        # lock access to this table
        with transaction.atomic():
            running_import = ImportHistory.objects.create(
                status="S", source_file=source
            )
        with transaction.atomic():
            start = time.time()
            log.info("Starting import ... (this may take several minutes)")
            num_obj, errors = parser.parse()
            for error in errors:
                log_details.append("Error in [%s]: %s" % (source, error))
            log.info(
                "Processed %s objects in %s (%s errors)"
                % (num_obj, source, len(errors))
            )
            stop = time.time()
            log_data = "\n".join(log_details)
            log.info("Import finished.. Time elapsed: %s s" % round(stop - start, 2))
        # finalise ImportHistory record
        with transaction.atomic():
            running_import.status = "C"
            running_import.details = log_data
            running_import.ended = timezone.now()
            running_import.save()
        print(
            "Import success. Processed %s objects Time elapsed: %s s"
            % (num_obj, round(stop - start, 2))
        )
