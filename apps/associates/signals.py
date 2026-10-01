from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.associates.models import Associate
from apps.associates.utils import health_certificate_file_name


@receiver(pre_save, sender=Associate)
def reset_health_certificate_reminder(sender, instance, **kwargs):
    """Re-arm the expiry reminder whenever a fresh certificate is stored.

    The flag is what keeps `notify_health_certificate_expiry` from mailing the
    same member on every run. Once a new certificate (or a corrected expiry
    date) is saved the warning should be allowed to fire again, so clear it
    here -- covering uploads from the admin UI, the public API and imports
    alike, rather than relying on each form to remember.
    """
    if not instance.pk:
        return

    if not health_certificate_file_name(instance):
        # No certificate being stored (e.g. a partial save of other fields):
        # leave the flag alone so an existing warning stays suppressed.
        return

    previous = (
        sender.objects.filter(pk=instance.pk)
        .values_list("health_certificate_file", "health_certificate_expiry_date")
        .first()
    )
    if not previous:
        return

    previous_file = previous[0] or ""
    if health_certificate_file_name(instance) != previous_file or (
        instance.health_certificate_expiry_date != previous[1]
    ):
        instance.health_certificate_reminder_sent = False