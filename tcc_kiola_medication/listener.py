from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save

from kiola.cares import const as cares_const
from kiola.cares import models as cares_models
from kiola.kiola_med import const as med_const
from kiola.kiola_med import models as med_models
from kiola.utils import const as kiola_const
from kiola.utils import logger
from kiola.utils.signals import signal_registry

log = logger.KiolaLogger(__name__).getLogger()
connected = False


def handle_new_prescription(sender, instance, **kwargs):
    """
    For create/update PrescriptionProfileRelation when a new prescription is created from the medication API
    """
    created = kwargs.get("created", None)
    if created:
        active_ppr = med_models.PrescriptionProfileRelation.objects.filter(
            active=True, root_profile__subject=instance.prescription.subject
        ).first()
        current_active_prescriptions = med_models.Prescription.objects.filter(
            subject=instance.prescription.subject,
            status__name=med_const.PRESCRIPTION_STATUS__ACTIVE,
        )

        # print('active_ppr', active_ppr)
        # check if exists current active PrescriptionProfileRelation
        # create a new one if not exist
        if active_ppr:
            pall = active_ppr.prescriptions.all()
            # print('pall', pall)
            existing = pall.filter(compound=instance.prescription.compound)

            # print('existing', existing)
            # check if the create prescription exists in the active PrescriptionProfileRelation
            # finish this process if alreaddy exist
            if len(existing) == 0:
                prescription = med_models.Prescription.objects.filter(
                    subject=instance.prescription.subject,
                    compound=instance.prescription.compound,
                    status__name=med_const.PRESCRIPTION_STATUS__ACTIVE,
                ).order_by("pk")
                # print('inactive_prescription', prescription.values_list('pk', flat=True))
                # check if there is a presciption use the same compound
                # create a new PrescriptionProfileRelation if not
                # put the existing prescription into PrescriptionProfileRelation so it will be replace in PrescriptionProfileRelation.objects.remove_and_update
                if len(prescription) > 1:
                    active_ppr.prescriptions.add(prescription[0])
                    active_ppr.save()
                else:
                    new_ppr = med_models.PrescriptionProfileRelation.objects.create_for_prescriptions(
                        current_active_prescriptions
                    )
        else:
            new_ppr = (
                med_models.PrescriptionProfileRelation.objects.create_for_prescriptions(
                    current_active_prescriptions
                )
            )


def disconnect():

    global connected
    post_save.disconnect(
        handle_new_prescription,
        sender=med_models.PrescriptionSchema,
        dispatch_uid="automatic_ppr_handler",
    )

    connected = False


def connect():

    global connected
    if not connected:

        post_save.connect(
            handle_new_prescription,
            sender=med_models.PrescriptionSchema,
            dispatch_uid="automatic_ppr_handler",
        )

        connected = True


# connect()
