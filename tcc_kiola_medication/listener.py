
from django.db.models.signals import post_save, pre_save, m2m_changed, post_delete

from kiola.utils.signals import signal_registry
from kiola.utils import const as kiola_const
from kiola.kiola_med import models as med_models
from kiola.kiola_med import const as med_const

from kiola.cares import const as cares_const, models as cares_models
from kiola.utils import logger


log = logger.KiolaLogger(__name__).getLogger()
connected = False

def handle_new_prescription(sender, instance, **kwargs):
    created = kwargs.get('created', None)
    if created: 
        active_ppr = med_models.PrescriptionProfileRelation.objects.filter(active=True, root_profile__subject=instance.prescription.subject).first()
        current_active_prescriptions = med_models.Prescription.objects.filter(subject=instance.prescription.subject, status__name=med_const.PRESCRIPTION_STATUS__ACTIVE)

        print('active_ppr', active_ppr)
        if active_ppr:
            pall = active_ppr.prescriptions.all()
            print('pall', pall)
            existing = pall.filter(compound=instance.prescription.compound)

            print('existing', existing)
            if len(existing) == 0:
                prescription = med_models.Prescription.objects.filter(
                      subject=instance.prescription.subject, 
                      compound=instance.prescription.compound,
                      status__name=med_const.PRESCRIPTION_STATUS__ACTIVE
                      ).order_by('pk')
                print('inactive_prescription', prescription.values_list('pk', flat=True))
                if len(prescription) > 1:
                    active_ppr.prescriptions.add(prescription[0])
                    active_ppr.save()
                else:
        #     ppr_prescriptions_pks = active_ppr.prescriptions.all()
        #     print('pks', ppr_prescriptions_pks)
        #     print('instance', instance.prescription)
        #     # if ppr.count() > 0:
        #     #     # prescriptions_changed = False
        #     if instance.prescription not in ppr_prescriptions_pks:

        #         # new_active_prescriptions = list(current_active_prescriptions).append(instance)
                    new_ppr = med_models.PrescriptionProfileRelation.objects.create_for_prescriptions(current_active_prescriptions)
                    print('added a new presction to ppr', new_ppr)

        else:
            new_ppr = med_models.PrescriptionProfileRelation.objects.create_for_prescriptions(current_active_prescriptions)
            print('create a new presction to ppr', new_ppr)



        # if len(selected_prescriptions) > 0:
        #     prescriptions = models.Prescription.objects.filter(subject=subject,
        #                                                        pk__in=selected_prescriptions)
        #     if len(prescriptions) != len(selected_prescriptions):
        #         messages.error(request, _("Unable to read selected prescriptions"))
        #     else:
        #         models.PrescriptionProfileRelation.objects.create_for_prescriptions(prescriptions)
        #         messages.success(request, _("Prescription monitoring updated"))
        # else:
        #     # find current PrescriptionProfileRelations and set to inactive
        #     pks = list(models.PrescriptionProfileRelation.objects.filter(active=True, root_profile__subject=subject).values_list("pk", flat=True))
        #     if pks:
        #         models.PrescriptionProfileRelation.objects.deactivate(pks, update_sop_status=True)
        #         messages.success(request, _("Removed prescription monitoring"))
        #     else:
        #         messages.error(request, _("No prescriptions selected"))


def disconnect():
  
    global connected
    post_save.disconnect(handle_new_prescription, sender=med_models.PrescriptionSchema, dispatch_uid="automatic_ppr_handler")

    connected = False


def connect():

    global connected
    if not connected:
        
        post_save.connect(handle_new_prescription, sender=med_models.PrescriptionSchema, dispatch_uid="automatic_ppr_handler")

        connected = True


connect()