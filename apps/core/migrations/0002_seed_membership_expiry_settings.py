from django.db import migrations

DEFAULTS = {
    "membership_expiry_mode": "fixed",
    "membership_expiry_fixed_date": "08-31",
    "membership_expiry_rolling_years": "1",
}


def seed_membership_expiry_settings(apps, schema_editor):
    Settings = apps.get_model("core", "Settings")
    for key, value in DEFAULTS.items():
        Settings.objects.get_or_create(key=key, defaults={"value": value})


def unseed_membership_expiry_settings(apps, schema_editor):
    Settings = apps.get_model("core", "Settings")
    Settings.objects.filter(key__in=DEFAULTS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seed_membership_expiry_settings, unseed_membership_expiry_settings
        ),
    ]
