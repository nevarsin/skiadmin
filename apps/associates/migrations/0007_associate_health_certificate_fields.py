from django.db import migrations, models

import apps.associates.utils


class Migration(migrations.Migration):

    dependencies = [
        ('associates', '0006_alter_associate_address_country_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='associate',
            name='health_certificate_file',
            field=models.FileField(blank=True, null=True, upload_to=apps.associates.utils.health_certificate_upload_to, verbose_name='Health certificate'),
        ),
        migrations.AddField(
            model_name='associate',
            name='health_certificate_expiry_date',
            field=models.DateField(blank=True, null=True, verbose_name='Health certificate expiry date'),
        ),
        migrations.AddField(
            model_name='associate',
            name='health_certificate_reminder_sent',
            field=models.BooleanField(default=False, help_text='Internal: set by the expiry reminder command, cleared when a new certificate is uploaded.', verbose_name='Health certificate reminder sent'),
        ),
    ]