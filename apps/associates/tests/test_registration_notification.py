from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.associates.models import Associate
from apps.associates.utils import (
    DEFAULT_REGISTRATION_NOTIFICATION_EMAIL,
    registration_notification_email,
)
from apps.core.models import Settings

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


class RegistrationNotificationEmailSettingTests(TestCase):
    """The admin mailbox is a site setting, like the membership policy."""

    def test_seeded_default(self):
        self.assertEqual(
            Settings.objects.get(key="registration_notification_email").value,
            "info@sciclubtarcento.it",
        )
        self.assertEqual(
            registration_notification_email(),
            DEFAULT_REGISTRATION_NOTIFICATION_EMAIL,
        )
        self.assertEqual(
            registration_notification_email(),
            "info@sciclubtarcento.it",
        )

    def test_setting_overrides_the_default(self):
        Settings.objects.update_or_create(
            key="registration_notification_email",
            defaults={"value": "board@example.com"},
        )
        self.assertEqual(registration_notification_email(), "board@example.com")

    def test_missing_setting_falls_back(self):
        Settings.objects.filter(key="registration_notification_email").delete()
        self.assertEqual(
            registration_notification_email(),
            DEFAULT_REGISTRATION_NOTIFICATION_EMAIL,
        )

    def test_blank_or_malformed_setting_disables_notification(self):
        for raw in ["", "   ", "not-an-email"]:
            with self.subTest(raw=repr(raw)):
                Settings.objects.update_or_create(
                    key="registration_notification_email",
                    defaults={"value": raw},
                )
                self.assertEqual(registration_notification_email(), "")

    def test_whitespace_around_a_valid_address_is_stripped(self):
        Settings.objects.update_or_create(
            key="registration_notification_email",
            defaults={"value": "  board@example.com  "},
        )
        self.assertEqual(registration_notification_email(), "board@example.com")


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class RegisterAssociateNotificationTests(TestCase):
    def register_payload(self, **overrides):
        data = {
            "first_name": "Mario",
            "last_name": "Rossi",
            "email": "mario@example.com",
            "address_street": "Via Roma",
            "address_number": "1",
            "address_city": "Tarcento",
            "address_zip": "33018",
            "birth_date": "1990-05-15",
            "birth_city": "Udine",
        }
        data.update(overrides)
        return data

    def test_registering_sends_an_admin_email(self):
        response = self.client.post(
            reverse("register_associate"),
            self.register_payload(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Associate.objects.filter(first_name="Mario", last_name="Rossi").exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["info@sciclubtarcento.it"])
        self.assertEqual(
            sent.body,
            "first_name: Mario\nlast_name: Rossi\nbirth_date: 1990-05-15",
        )
        self.assertNotIn("mario@example.com", sent.body)
        self.assertNotIn("Via Roma", sent.body)

    def test_registering_honours_a_custom_mailbox(self):
        Settings.objects.update_or_create(
            key="registration_notification_email",
            defaults={"value": "board@example.com"},
        )
        self.client.post(reverse("register_associate"), self.register_payload())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["board@example.com"])

    def test_blank_mailbox_skips_sending(self):
        Settings.objects.update_or_create(
            key="registration_notification_email",
            defaults={"value": ""},
        )
        response = self.client.post(
            reverse("register_associate"),
            self.register_payload(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Associate.objects.filter(first_name="Mario", last_name="Rossi").exists()
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_registration_does_not_send_email(self):
        response = self.client.post(
            reverse("register_associate"),
            self.register_payload(first_name=""),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Associate.objects.filter(last_name="Rossi").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_staff_created_associates_are_not_notified(self):
        response = self.client.post(
            reverse("add_associates"),
            {
                "first_name": "Giulia",
                "last_name": "Bianchi",
                "email": "giulia@example.com",
                "membership_type": "standard",
                "expiration_date": "2027-08-31",
                "address_street": "Via Roma",
                "address_number": "1",
                "address_city": "Tarcento",
                "address_zip": "33018",
                "address_province": "UD",
                "address_country": "Italy",
                "birth_date": "1985-03-20",
                "birth_city": "Udine",
                "birth_province": "UD",
                "birth_country": "Italy",
                "fiscal_code": "BNCGLI85C60L483X",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Associate.objects.filter(first_name="Giulia", last_name="Bianchi").exists()
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_mail_failure_does_not_fail_registration(self):
        with patch(
            "apps.associates.utils.EmailMessage.send",
            side_effect=OSError("smtp down"),
        ):
            response = self.client.post(
                reverse("register_associate"),
                self.register_payload(),
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Associate.objects.filter(first_name="Mario", last_name="Rossi").exists()
        )
