from django.db import migrations

DEFAULTS = {
    "health_certificate_warn_days": "15",
}


def seed_health_certificate_settings(apps, schema_editor):
    Settings = apps.get_model("core", "Settings")
    for key, value in DEFAULTS.items():
        Settings.objects.get_or_create(key=key, defaults={"value": value})


def unseed_health_certificate_settings(apps, schema_editor):
    Settings = apps.get_model("core", "Settings")
    Settings.objects.filter(key__in=DEFAULTS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_seed_membership_expiry_settings"),
    ]

    operations = [
        migrations.RunPython(
            seed_health_certificate_settings, unseed_health_certificate_settings
        ),
    ]