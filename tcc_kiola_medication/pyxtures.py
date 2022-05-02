from email.policy import default

from diplomat.models import ISOCountry, ISOLanguage
from reversion import revisions as reversionrevisions

from kiola.cares import const as cares_const
from kiola.kiola_configuration import const as configuration_const
from kiola.kiola_configuration import models as configuration
from kiola.kiola_med import const as med_const
from kiola.kiola_med import models as med_models
from kiola.kiola_senses import const as senses_const
from kiola.kiola_senses import models as senses_models
from kiola.utils.commons import get_system_user
from kiola.utils.pyxtures import Pyxture as BasePyxture

from . import const, models, utils


class Pyxture(BasePyxture):
    def default(self):
        self.setup_medication_observation_profile()
        self.create_patient_enter_compound_source()
        self.create_default_medication_list()
        self.set_up_extra_meds()
        self.generate_default_medication_types()

    def dev(self):
        self.setup_medication_observation_profile()
        self.create_patient_enter_compound_source()
        self.create_default_medication_list()
        self.set_up_extra_meds()
        self.generate_default_medication_types()

    def setup_medication_observation_profile(self):

        (
            root,
            created,
        ) = senses_models.ObservationProfile.objects.get_or_create_root_profile()
        time_profile = senses_models.DateTimeObservationProfile.objects.get(
            name=senses_const.MDC_ATTR_TIME_ABS
        )

        (
            med_ob,
            created,
        ) = senses_models.ExtensibleRootObservationProfile.objects.get_or_create(
            name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION
        )

        self._create_enum_observation(
            parent=med_ob,
            obs_name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION,
            num_occurences=senses_const.ONE,
            enum_type=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUMTYPE,
            enum_list=[
                const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_TAKE,
                const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_NOT_TAKE,
                const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_ACTION_ENUM_UNDO,
            ],
        )
        self._create_datetime_observation(
            parent=med_ob,
            obs_name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_TIME,
            num_occurences=senses_const.ONE,
        )

        # Reference to previous AE Observaton ID
        self._create_text_observation(
            parent=med_ob,
            obs_name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_MEDICATION_ID,
            num_occurences=senses_const.ONE,
        )
        self._create_text_observation(
            parent=med_ob,
            obs_name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ID,
            num_occurences=senses_const.ONE,
        )
        self._create_text_observation(
            parent=med_ob,
            obs_name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ACTION_TIME,
            num_occurences=senses_const.ONE,
        )
        self._create_text_observation(
            parent=med_ob,
            obs_name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION_SCHEDULE_ACTION_DATE,
            num_occurences=senses_const.ONE,
        )

        senses_models.RelatedObservationProfile.objects.get_or_create(
            parent=med_ob, child=time_profile, num_occurences=senses_const.ONE
        )
        senses_models.RelatedObservationProfile.objects.get_or_create(
            parent=root, child=med_ob, num_occurences=senses_const.ZERO_OR_MORE
        )

        self._add_frontends_to_profile(med_ob)

        senses_models.ObservationProfile.objects.activate(
            name=const.MDC_DEV_SPEC_PROFILE_TCC_MED_PRESCRIPTION_OBSERVATION
        )

    def _add_frontends_to_profile(self, profile):
        """
        Set up api query permissions for root observation profiles and their children profiles
        """
        # add frontends by default: webinterface and mobilemonitor (and api, already set)
        web = senses_models.Frontend.objects.get(
            name=senses_const.FRONTEND__WEBFRONTEND
        )
        mm = senses_models.Frontend.objects.get(
            name=cares_const.FRONTEND__MOBILE_MONITOR
        )
        cwd = senses_models.Frontend.objects.get(
            name=cares_const.FRONTEND__CARES_WEB_DEVICE
        )
        api = senses_models.Frontend.objects.get(name=senses_const.FRONTEND__API)

        profile.frontends.add(api)
        profile.frontends.add(web)
        profile.frontends.add(mm)
        profile.frontends.add(cwd)

        children = profile.children.all()
        for child in children:
            child.frontends.add(web)
            child.frontends.add(api)
            child.frontends.add(mm)
            child.frontends.add(cwd)

    def _create_enum_observation(
        self, parent, obs_name, num_occurences, enum_type, enum_list
    ):
        (
            new_enumtype,
            _created,
        ) = senses_models.EnumerationType.objects.get_or_create_from_list(
            name=enum_type,
            values=[("en", enum_list)],
            use_internal_name_scheme=False,
        )
        (
            new_obs,
            _created,
        ) = senses_models.EnumerationObservationProfile.objects.get_or_create(
            name=obs_name, enum_type=new_enumtype
        )
        senses_models.RelatedObservationProfile.objects.get_or_create(
            parent=parent, child=new_obs, num_occurences=num_occurences
        )

    def _create_text_observation(self, parent, obs_name, num_occurences):
        new_obs, _created = senses_models.TextObservationProfile.objects.get_or_create(
            name=obs_name
        )
        senses_models.RelatedObservationProfile.objects.get_or_create(
            parent=parent, child=new_obs, num_occurences=num_occurences
        )

    def _create_datetime_observation(self, parent, obs_name, num_occurences):

        (
            new_obs,
            created,
        ) = senses_models.DateTimeSimpleObservationProfile.objects.get_or_create(
            name=obs_name
        )
        senses_models.RelatedObservationProfile.objects.get_or_create(
            parent=parent, child=new_obs, num_occurences=num_occurences
        )

    def create_patient_enter_compound_source(self):

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

    def create_default_medication_list(self):
        configuration.ConfigurationType.objects.get_or_create(
            name=configuration_const.CONFIGURATION_TYPE__JSON,
            converter=configuration_const.CONFIGURATION_TYPE__JSON,
        )
        configuration.ConfigurationItem.objects.set_configuration(
            const.TCC_MEDS_CONFIGURATION_CATEGORY,
            const.TCC_MEDS_DEFAULT_MEDICINE_LIST,
            const.DEFAULT_MEDICATION_LIST,
            config_type=configuration_const.CONFIGURATION_TYPE__JSON,
        )

    def set_up_extra_meds(self):
        # get patient compound source
        source = med_models.CompoundSource.objects.get(
            name=const.COMPOUND_SOURCE_NAME__TCC,
            version=const.COMPOUND_SOURCE_VERSION__PATIENT,
        )
        current_num = med_models.Compound.objects.filter(source=source).count()
        uid = f"{const.PATIENT_ENTERED_COMPOUND_UID_PREFIX}-{current_num+1}"
        # create or update compound data
        unit, created = med_models.TakingUnit.objects.get_or_create(name="Injection")
        if created:
            unit.descrition = "INJ"
            unit.save

        # create active components
        ac, created = med_models.ActiveComponent.objects.get_or_create(
            name="evolocumab"
        )
        if created:
            ac.name_ref = uid
            ac.save()

        # create or update compound data
        compound, created = med_models.Compound.objects.get_or_create(
            uid=uid,
            name="evolocumab",
            source=source,
            dosage_form="Injection",
            dosage_form_ref="INJ",
            registration_number="system",
        )
        active_components = compound.active_components.all()
        compound.active_components.add(ac)
        compound.save()

        prn, created = models.CompoundExtraInformation.objects.get_or_create(
            compound=compound, name=const.COMPOUND_EXTRA_INFO_NAME__MEDICATION_TYPE
        )
        if created:
            prn.value = "Regular"
            prn.save()

    def generate_default_medication_types(self):
        reg, _ = models.MedicationType.objects.get_or_create(
            name=const.MEDICATION_TYPE_VALUE__REGULAR, description="Regular medication"
        )
        prn, _ = models.MedicationType.objects.get_or_create(
            name=const.MEDICATION_TYPE_VALUE__PRN, description="PRN medication"
        )
