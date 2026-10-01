from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0002_copy_certifications_to_associates"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="subscription",
            name="certification_exp_date",
        ),
        migrations.RemoveField(
            model_name="subscription",
            name="certification_file",
        ),
    ]