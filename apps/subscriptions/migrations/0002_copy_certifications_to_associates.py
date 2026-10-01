from django.db import migrations
from django.db.models import F


def copy_certifications_to_associates(apps, schema_editor):
    """Move per-subscription health certificates onto the Associate.

    The certificate used to hang off the Subscription, which meant uploading a
    fresh copy for every single trunk of an activity even though it was the same
    document all season. It now lives on the Associate instead.

    A member may hold several subscriptions, so rows are walked oldest-first
    and each write overwrites the last: the row with the furthest-away expiry
    date wins, which is the certificate that stays valid longest.
    """
    Associate = apps.get_model("associates", "Associate")
    Subscription = apps.get_model("subscriptions", "Subscription")

    queryset = (
        Subscription.objects
        .exclude(associate_id=None)
        .exclude(certification_file="")
        .select_related("associate")
        .order_by(
            F("certification_exp_date").asc(nulls_last=True),
            "season",
            "pk",
        )
    )

    for subscription in queryset:
        Associate.objects.filter(pk=subscription.associate_id).update(
            health_certificate_file=subscription.certification_file.name,
            health_certificate_expiry_date=subscription.certification_exp_date,
            health_certificate_reminder_sent=False,
        )


def noop(apps, schema_editor):
    """Certificates now live on the Associate; reversing cannot put them back."""


class Migration(migrations.Migration):

    dependencies = [
        ("associates", "0007_associate_health_certificate_fields"),
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_certifications_to_associates, noop),
    ]