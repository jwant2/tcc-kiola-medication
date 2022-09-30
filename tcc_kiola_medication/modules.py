from django.conf import settings
from django.utils.translation import get_language, ugettext
from django.utils.translation import ugettext_lazy as _

from kiola.cares import const as cares_const
from kiola.cares import modules as cares_modules
from kiola.utils.modules import (
    Dashboard,
    DashboardModule,
    dashboard_registry,
    module_registry,
)

from . import tables


class TablesModule(DashboardModule):
    title = _("Tables")
    template = "modules/tablelist.html"
    link = ""
    name = "tablelistmodule"
    permissions = []

    class Media:
        js = (
            "daterangepicker/daterangepicker.js",
            "daterangepicker/daterangepicker-select.patch.js",
            settings.KIOLA_THEMES.get("frontend") + "/js/bootstrap-multiselect.js",
            "kiola-ace-extensions/bootstrap-multiselect-ace-fix.js",
            "jscookie/js.cookie.js",
            "js/ie-svg-jquery-fix.js",
        )
        css = {
            "all": (
                "css/kiola-fonts.css",
                "css/hc-tooltip.css",
                settings.KIOLA_THEMES.get("frontend")
                + "/css/bootstrap-multiselect.css",
            )
        }

    def prepare(self):
        self.vars["tablelists"] = [tables.MedicationAdherenceOverview(self.request)]
        self.vars["title"] = self.title


def register_tablelist_module():
    if TablesModule.name not in list(module_registry.modules):
        module_registry.register(TablesModule)
