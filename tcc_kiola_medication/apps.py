# -*- coding: utf-8 -*-
import os.path

from appconf import AppConf
from django.apps import AppConfig, apps
from django.conf import settings

from kiola.utils import logger

log = logger.KiolaLogger(__name__).getLogger()


class SiteAppConf(AppConf):
    TEMPLATE_DIRS = []
    TEMPLATES = []

    def _get_template_dirs(self):

        try:
            dirs = [] + list(settings.TEMPLATE_DIRS)
        except BaseException:
            dirs = [] + list(settings.TEMPLATES[0]["DIRS"])
        dirs.insert(1, os.path.dirname(__file__) + "/templates/")

        return dirs

    def configure_template_dirs(self, value):

        return self._get_template_dirs()

    def configure_templates(self, value):
        templates = [] + list(settings.TEMPLATES)
        templates[0].update({"DIRS": self._get_template_dirs()})
        return templates

    class Meta:
        prefix = ""


class TccKiolaMedicationConfig(AppConfig):
    name = "tcc_kiola_medication"
    verbose_name = "TCC Kiola Medications"

    def ready(self):
        from kiola.kiola_med import models as med_models

        from . import modules, utils

        med_models.CompoundManager.adapters["TCC"] = utils.TCCAdapter
        settings.LOGGING["loggers"].update(
            {
                "tcc_kiola_medication": {
                    "handlers": ["syslog"],
                    "level": "INFO",
                }
            }
        )

        modules.register_tablelist_module()
