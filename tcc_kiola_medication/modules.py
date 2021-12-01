

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
    name = "tablesmodule"
    permissions = []

    class Media:
        js = (
            'daterangepicker/daterangepicker.js',
            'daterangepicker/daterangepicker-select.patch.js',
            settings.KIOLA_THEMES.get("frontend") + '/js/bootstrap-multiselect.js',
            'kiola-ace-extensions/bootstrap-multiselect-ace-fix.js',
            'jscookie/js.cookie.js',
            'js/ie-svg-jquery-fix.js')
        css = {'all': ('css/kiola-fonts.css',
                       'css/hc-tooltip.css',
                       settings.KIOLA_THEMES.get("frontend") + '/css/bootstrap-multiselect.css')}


    def prepare(self):
        self.vars["patientlists"] = [tables.MedicationAdherenceOverview(self.request)]
        self.vars["title"] = self.title


module_registry.register(TablesModule)

class PatientHelpdeskDashboard(cares_modules.PatientHelpdeskDashboard):
    """ This Dashboard is the main patient dashboard
    """

    def init_with_context(self, context):
        super().init_with_context(context)
        self.modules.insert(1, module_registry.modules["tablesmodule"])


del dashboard_registry.dashboards[cares_const.DASHBOARD__CARES_PATIENT_HELPDESK]
dashboard_registry.register(
    PatientHelpdeskDashboard, name=cares_const.DASHBOARD__CARES_PATIENT_HELPDESK
)

class PatientAdminDashboard(cares_modules.PatientHelpdeskDashboard):
    """ This Dashboard is used to extend the PatientDashboard for Users
        with access to the Kiola Admin Backend (staff users)
    """

    def init_with_context(self, context):
        super(PatientAdminDashboard, self).init_with_context(context)
        self.modules.insert(1, module_registry.modules["tablesmodule"])


del dashboard_registry.dashboards[cares_const.DASHBOARD__CARES_PATIENT_ADMIN]
dashboard_registry.register(
    PatientHelpdeskDashboard, name=cares_const.DASHBOARD__CARES_PATIENT_ADMIN
)
