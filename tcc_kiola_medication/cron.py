
import random
from datetime import datetime, timedelta, date, time
from django.db.models import Q, F, Prefetch, OuterRef, Subquery
from django.utils import timezone
from reversion import revisions as reversion
from django_cron import CronJobBase, Schedule
from django.utils.timezone import now, get_current_timezone, make_aware
from django.apps import apps
from kiola.utils.commons import get_system_user
from kiola.kiola_senses import models as senses_models, const as senses_const
from kiola.utils import logger
from kiola.kiola_clients import signals
from kiola.utils import const as kiola_const
from kiola.kiola_med import models as med_models, const as med_const
from kiola.kiola_export import models as export_models, const as export_const
from kiola.kiola_messaging import models as msg_models
if apps.is_installed("django_dashmin"):
    from django_dashmin.models import AdminNotification as BackendNotification
else:
    from kiola.kiola_admin.models import BackendNotification

from . import const, utils, models

log = logger.KiolaLogger(__name__).getLogger()

class ScheduleTakingReminderJob(CronJobBase):
  
    RUN_EVERY_MINS = 10
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = "tcc_kiola_medication.schedule_taking_reminder_job"
    err_str = ""

    def _should_send_reminder(self, subject, compound_name, time, now):
        '''
        Check if it is time to send out medication reminder
        '''
        schedule_time = now.replace(hour=time.hour, minute=time.minute, second=time.second)
        time_diff = (now - schedule_time).total_seconds() / 60
        # skip checking 
        if time_diff < const.MEDICATION_REMINDER_TIME_MINUTES or time_diff > 60: return False
        text = const.MEDICATION_REMINDER__MESSAGE_BODY % (compound_name, time)
        # check if reminder exists
        messages = msg_models.SubjectMessage.objects.filter(
          recipients__user__id__exact=subject.login.id,
          created__lte=now,
          created__gte=schedule_time,
          messagebody__body=text
        )
        if messages.count() > 0: 
            return False
        return True

    def _get_taking_time(self, subject, taking):
        if taking.timepoint.name == "custom":
            time = taking.taking_time
        else:
            user_pref = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, subject.login)
            if user_pref is None:
                utils.set_default_user_pref_med_time_values(subject.login)
                user_pref = models.UserPreferenceConfig.objects.get_value(const.USER_PREFERENCE_KEY__MEDICATION_TIMES, subject.login)
            time_value = user_pref[f'{const.USER_PREFERENCE_CONFIG_PREFIX}{taking.timepoint.name}']
            time = datetime.strptime(time_value['actualTime'], "%H:%M").time()
        return time

    def do(self):
        print("running", self.code)
        with reversion.create_revision():
            reversion.set_user(get_system_user())
            now = datetime.now(timezone.get_current_timezone())
            ## active schedules only
            schedule_takings = models.ScheduledTaking.objects.filter(
                Q(end_date__gte=now, start_date__lte=now) | Q(start_date__lte=now, end_date=None),
                active=True,
                reminder=True,
                takings_set__status__name=med_const.PRESCRIPTION_STATUS__ACTIVE,
                takings_set__subject__subjectstatus__status__level__gte=100 # active subject only
            ).annotate(prescr_id=
                F('takings_set__id')
            )
            takings = utils.filter_schedule_for_given_date(now, schedule_takings)
            for taking in takings:
                try:
                    prescription = models.TCCPrescription.objects.prefetch_related("subject", "compound").get(pk=taking.prescr_id)
                    subject = prescription.subject
                    time = self._get_taking_time(subject, taking)
                    should_send = self._should_send_reminder(subject, prescription.compound.name, time, now)
                    if not should_send: continue
                    try:
                        utils.send_medication_reminder_notification(subject, taking, time, prescription.compound.name)
                    except Exception as error:
                        err_msg= f" failed to send medication reminder {str(taking)} - {str(error)}"
                        self.err_str += err_msg + "\n"
                        print(err_msg, error)
                        import traceback

                        self.err_str += "" + traceback.format_exc()
                        print(traceback.format_exc())
                        BackendNotification.objects.create_backend_notification(get_system_user(), err_msg, traceback.format_exc())

                except Exception as error:
                    err_msg = f" failed to process medication reminder {str(taking)} - {str(error)}"
                    self.err_str += err_msg+ "\n"
                    print(err_msg, error)
                    import traceback

                    self.err_str += "" + traceback.format_exc()
                    print(traceback.format_exc())
                    BackendNotification.objects.create_backend_notification(get_system_user(), err_msg, traceback.format_exc())

        return self.err_str