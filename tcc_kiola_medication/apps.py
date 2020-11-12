# -*- coding: utf-8 -*-
import os.path
from django.apps import AppConfig, apps
from django.conf import settings
from appconf import AppConf

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
        print('dirs', dirs)
        return dirs

    def configure_template_dirs(self, value):

        return self._get_template_dirs()

    def configure_templates(self, value):
        templates = [] + list(settings.TEMPLATES)
        templates[0].update({"DIRS": self._get_template_dirs()})
        return templates

    class Meta:
        prefix = ''





class TccKiolaMedicationConfig(AppConfig):
    name = 'tcc_kiola_medication'
    verbose_name = "TCC Kiola Medications"
