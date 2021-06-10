
from kiola.cares import const as cares_const
from django.utils.translation import ugettext_lazy as _, ugettext_noop, pgettext_lazy, get_language

ADVERSE_REACTION_TYPE__ALLERGY = ugettext_noop("Allergy")
ADVERSE_REACTION_TYPE__SIDE_EFFECT = ugettext_noop("Side Effect")
ADVERSE_REACTION_TYPE__INTOLERANCE = ugettext_noop("Intolerance")
ADVERSE_REACTION_TYPE__IDIOSYNCRATIC = ugettext_noop("Idiosyncratic")
ADVERSE_REACTION_TYPE__UNKNOWN = ugettext_noop("Unknown")

USER_PREFERENCE_KEY__MEDICATION_TIMES = ugettext_noop("USER_PREFERENCE__MEDICATION_TIMES")
USER_PREFERENCE_CONFIG_PREFIX = ugettext_noop("timepoint_type__")
MEDICATION_TIMES_DEFAULT_VALUES = {
   f"{USER_PREFERENCE_CONFIG_PREFIX}morning": {"type": "morning", "actualTime": "08:00"},
   f"{USER_PREFERENCE_CONFIG_PREFIX}noon": {"type": "noon", "actualTime": "12:00"},
   f"{USER_PREFERENCE_CONFIG_PREFIX}afternoon": {"type": "afternoon", "actualTime": "18:00"},
   f"{USER_PREFERENCE_CONFIG_PREFIX}night": {"type": "night", "actualTime": "22:00"},
}

TAKING_TIMEPOINT__AFTERNOON = ugettext_noop("afternoon")
TAKING_TIMEPOINT__CUSTOM = ugettext_noop("custom")

TAKING_FREQUENCY_VALUE__ONCE = ugettext_noop("once")
TAKING_FREQUENCY_VALUE__DAILY = ugettext_noop("daily")
TAKING_FREQUENCY_VALUE__WEEKLY = ugettext_noop("weekly")
TAKING_FREQUENCY_VALUE__FORTNIGHTLY = ugettext_noop("fortnightly")
TAKING_FREQUENCY_VALUE__MONTHLY = ugettext_noop("monthly")

TAKING_SCHEMA_TYPE__SCHEDULED = "S"

COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE = ugettext_noop("medication_type")

MEDICATION_TYPE_VALUE__PRN = ugettext_noop("PRN")
MEDICATION_TYPE_VALUE__REGULAR = ugettext_noop("Regular")
MEDICATION_TYPE_VALUES = [MEDICATION_TYPE_VALUE__PRN, MEDICATION_TYPE_VALUE__REGULAR]

COMPOUND_SOURCE_NAME__TCC = "TCC Kiola Medication"
COMPOUND_SOURCE_VERSION__PATIENT = ugettext_noop("patient")
COMPOUND_SOURCE_DESCRIPTION__PATIENT_ENTERED = ugettext_noop("Patient entered")
COMPOUND_SOURCE_DESCRIPTION__ADMIN_IMPORT = ugettext_noop("Admin imported")
PATIENT_ENTERED_COMPOUND_UID_PREFIX = "ptd"

# medication observation profile
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION = ugettext_noop("MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION")
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION = ugettext_noop("MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION")
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUMTYPE = ugettext_noop("MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUMTYPE")
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_MEDICATION_ID = ugettext_noop("MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_MEDICATION_ID")
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ID = ugettext_noop("MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ID")
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_TIME = ugettext_noop("MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_TIME")
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ACTION_TIME = ugettext_noop("MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ACTION_TIME")
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ACTION_DATE = ugettext_noop("MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ACTION_DATE")

MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_TAKE = ugettext_noop("take")
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_NOT_TAKE = ugettext_noop("not_take")
MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_UNDO = ugettext_noop("undo")

CHART_CATEGORY__TCC_MEDICATION = ugettext_noop("TCC_MEDICATION")

MEDICATION_REMINDER_TIME_MINUTES = 10

MEDICATION_REMINDER__MESSAGE_BODY = "Please take your medication - %s. It was due on %s"


TCC_MEDS_CONFIGURATION_CATEGORY = 'TCC.Medication'
TCC_MEDS_DEFAULT_MEDICINE_LIST = ugettext_noop("TCC_MEDS_DEFAULT_MEDICINE_LIST")
DEFAULT_MEDICATION_LIST = [
  'amiodarone', 
  'amlodipine', 
  'apixaban', 
  'aspirin', 
  'bisoprolol', 
  'candesartan', 
  'carvedilol', 
  'clopidogrel', 
  'dabigatran', 
  'digoxin', 
  'diltiazem', 
  'empagliflozin', 
  'frusemide', 
  'furosemide (frusemide)', 
  'hydrochlorothiazide', 
  'indapamide', 
  'irbesartan', 
  'isosorbide mononitrate',
  'lercanidipine', 
  'lisinopril', 
  'metoprolol', 
  'nebivolol', 
  'nicorandil', 
  'perindopril', 
  'ramipril', 
  'rivaroxaban', 
  'sacubitril-valsartan', 
  'sotalol', 
  'spironolactone', 
  'ticagrelor', 
  'trandolapril', 
  'valsartan', 
  'verapamil', 
  'warfarin',
  'rosuvastatin',
  'atorvastatin',
  'pravastatin',
  'simvastatin',
  'fluvastatin',
  'ezetimibe',
  'ezetimibe-atorvastatin',
  'ezetimibe-rosuvastatin',
  'ezetimibe-simvastatin',
  'fenofibrate',
  'omega-3 fatty acids',
  'evolocumab',
]