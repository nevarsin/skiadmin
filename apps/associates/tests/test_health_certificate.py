import shutil
import tempfile
from datetime import date
from io import StringIO

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.associates.utils import (
    DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS,
    health_certificate_status,
    health_certificate_upload_to,
    health_certificate_warn_days,
)
from apps.core.models import Settings
from apps.subscriptions.models import Subscription

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


def _make_associate(**overrides):
    data = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "address_street": "Via Roma",
        "address_number": "1",
        "address_city": "Tarcento",
        "address_zip": "33018",
        "birth_date": date(1990, 1, 1),
        "birth_city": "Tarcento",
    }
    data.update(overrides)
    return Associate.objects.create(**data)


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class HealthCertificateWarnDaysSettingTests(TestCase):
    """`health_certificate_warn_days` is a site setting, like the membership policy."""

    def test_seeded_default(self):
        self.assertEqual(health_certificate_warn_days(), DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS)
        self.assertEqual(health_certificate_warn_days(), 15)

    def test_setting_overrides_the_default(self):
        Settings.objects.filter(key="health_certificate_warn_days").update(value="30")
        self.assertEqual(health_certificate_warn_days(), 30)

    def test_missing_setting_falls_back(self):
        Settings.objects.filter(key="health_certificate_warn_days").delete()
        self.assertEqual(health_certificate_warn_days(), DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS)

    def test_malformed_setting_falls_back(self):
        for raw in ["", "   ", "abc", "15.5"]:
            with self.subTest(raw=raw):
                Settings.objects.filter(key="health_certificate_warn_days").update(value=raw)
                self.assertEqual(health_certificate_warn_days(), DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS)

    def test_negative_setting_falls_back(self):
        Settings.objects.filter(key="health_certificate_warn_days").update(value="-5")
        self.assertEqual(health_certificate_warn_days(), DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS)


class HealthCertificateUploadToTests(TestCase):
    def test_path_includes_date_and_expiry(self):
        associate = _make_associate(first_name="Ada", last_name="Lovelace")
        associate.health_certificate_expiry_date = date(2027, 3, 4)
        today = timezone.now().strftime("%Y%m%d")
        path = health_certificate_upload_to(associate, "scan.jpg")
        self.assertEqual(
            path,
            f"health_certificates/{today}/HealthCertificate_Ada_Lovelace_20270304.jpg",
        )

    def test_extension_is_preserved(self):
        """Members send pdf, jpg and jpeg alike, so the extension must survive."""
        associate = _make_associate()
        for name in ["scan.pdf", "scan.jpg", "scan.jpeg", "scan.xls"]:
            with self.subTest(name=name):
                path = health_certificate_upload_to(associate, name)
                self.assertEqual(path.rsplit(".", 1)[1], name.rsplit(".", 1)[1])
                self.assertTrue(path.startswith("health_certificates/"))

    def test_missing_extension_defaults_to_pdf(self):
        associate = _make_associate()
        self.assertTrue(health_certificate_upload_to(associate, "scan").endswith(".pdf"))

    def test_missing_expiry_is_labelled_noexp(self):
        associate = _make_associate()
        self.assertIn("noexp", health_certificate_upload_to(associate, "scan.pdf"))


class HealthCertificateStatusTests(TestCase):
    today = date(2026, 10, 5)

    def status_for(self, file_name="health_certificates/cert.pdf", expiry=None):
        associate = _make_associate()
        associate.health_certificate_file = file_name
        associate.health_certificate_expiry_date = expiry
        return health_certificate_status(associate, today=self.today, warn_days=15)

    def test_missing_when_no_file(self):
        code, days_left = self.status_for(file_name="", expiry=date(2027, 1, 1))
        self.assertEqual(code, "missing")
        self.assertIsNone(days_left)

    def test_valid_far_from_expiry(self):
        self.assertEqual(self.status_for(expiry=date(2026, 11, 1))[0], "valid")

    def test_expiring_inside_the_window(self):
        code, days_left = self.status_for(expiry=date(2026, 10, 20))
        self.assertEqual(code, "expiring")
        self.assertEqual(days_left, 15)

    def test_boundary_of_the_window_is_still_expiring(self):
        self.assertEqual(self.status_for(expiry=date(2026, 10, 10))[0], "expiring")

    def test_day_after_the_window_is_valid(self):
        # 2026-10-21 is 16 days out, one past the 15-day window.
        self.assertEqual(self.status_for(expiry=date(2026, 10, 21))[0], "valid")

    def test_expiring_today_is_not_expired(self):
        """Mirrors memberships: the expiry date itself is still covered.

        It still counts as `expiring`, which is the whole point -- the member
        gets one last chance while the certificate is technically valid.
        """
        self.assertEqual(self.status_for(expiry=self.today)[0], "expiring")

    def test_yesterday_is_expired(self):
        code, days_left = self.status_for(expiry=date(2026, 10, 4))
        self.assertEqual(code, "expired")
        self.assertEqual(days_left, -1)

    def test_warn_days_setting_widens_the_window(self):
        associate = _make_associate()
        associate.health_certificate_file = "health_certificates/cert.pdf"
        associate.health_certificate_expiry_date = date(2026, 11, 20)
        self.assertEqual(
            health_certificate_status(associate, today=self.today, warn_days=15)[0], "valid"
        )
        self.assertEqual(
            health_certificate_status(associate, today=self.today, warn_days=60)[0], "expiring"
        )

    def test_file_without_expiry_counts_as_compliant(self):
        """No recorded expiry means nothing to chase, so do not flag the member."""
        self.assertEqual(self.status_for(expiry=None)[0], "valid")

    def test_warn_days_falls_back_to_the_setting_when_not_given(self):
        Settings.objects.filter(key="health_certificate_warn_days").update(value="60")
        associate = _make_associate()
        associate.health_certificate_file = "health_certificates/cert.pdf"
        associate.health_certificate_expiry_date = date(2026, 11, 20)
        # 46 days out: outside the default 15-day window, inside a 60-day one.
        self.assertEqual(
            health_certificate_status(associate, today=self.today, warn_days=15)[0], "valid"
        )
        self.assertEqual(health_certificate_status(associate, today=self.today)[0], "expiring")


class HealthCertificateReminderFlagTests(TestCase):
    """A fresh upload must re-arm the reminder, or the club stops chasing."""

    def setUp(self):
        # Uploads must land somewhere disposable, not in the repo's media/.
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, True)
        media_override = override_settings(MEDIA_ROOT=media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)

    def associate_with_certificate(self, file_name="health_certificates/old.pdf", expiry=date(2026, 10, 1)):
        associate = _make_associate()
        associate.health_certificate_file = file_name
        associate.health_certificate_expiry_date = expiry
        associate.save()
        # Set the flag with a queryset update so the pre_save signal does not
        # helpfully clear it for us: storing the certificate above is exactly
        # the event that re-arms the reminder.
        Associate.objects.filter(pk=associate.pk).update(health_certificate_reminder_sent=True)
        associate.refresh_from_db()
        self.assertTrue(associate.health_certificate_reminder_sent)
        return associate

    def test_uploading_a_new_certificate_resets_the_flag(self):
        associate = self.associate_with_certificate()
        upload = SimpleUploadedFile("new.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        associate.health_certificate_file = upload
        associate.save()
        associate.refresh_from_db()
        self.assertFalse(associate.health_certificate_reminder_sent)

    def test_correcting_the_expiry_date_resets_the_flag(self):
        associate = self.associate_with_certificate()
        associate.health_certificate_expiry_date = date(2027, 10, 1)
        associate.save()
        associate.refresh_from_db()
        self.assertFalse(associate.health_certificate_reminder_sent)

    def test_unrelated_save_keeps_the_flag(self):
        associate = self.associate_with_certificate()
        associate.phone = "333 1234567"
        associate.save()
        associate.refresh_from_db()
        self.assertTrue(associate.health_certificate_reminder_sent)
        self.assertEqual(associate.phone, "333 1234567")


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class NotifyHealthCertificateExpiryTests(TestCase):
    today = date(2026, 10, 5)

    def make(self, expiry=None, file_name="health_certificates/cert.pdf", **overrides):
        """An associate enrolled in gymnastics, with a certificate on file."""
        associate = _make_associate(**overrides)
        associate.health_certificate_file = file_name
        associate.health_certificate_expiry_date = expiry
        associate.save()
        article = Article.objects.create(
            name="Presciistica", price=50, category="gymnastics",
            type="course", certification_required=True,
        )
        Subscription.objects.create(
            article=article, associate=associate, season=self.today,
        )
        return associate

    def notify(self, **options):
        out = StringIO()
        call_command("notify_health_certificate_expiry", stdout=out, today=self.today, **options)
        return out.getvalue()

    def test_warns_when_inside_the_window(self):
        associate = self.make(expiry=date(2026, 10, 10))
        self.notify()
        associate.refresh_from_db()
        self.assertTrue(associate.health_certificate_reminder_sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(associate.email, mail.outbox[0].to)

    def test_does_not_warn_far_from_expiry(self):
        self.make(expiry=date(2027, 6, 1))
        self.notify()
        self.assertEqual(len(mail.outbox), 0)

    def test_does_not_warn_twice(self):
        """The whole point of the flag: a daily cron must not mail every day."""
        self.make(expiry=date(2026, 10, 10))
        self.notify()
        self.notify()
        self.assertEqual(len(mail.outbox), 1)

    def test_cleared_expiry_date_never_warns(self):
        self.make(expiry=None)
        self.notify()
        self.assertEqual(len(mail.outbox), 0)

    def test_expired_certificate_is_emailed_and_cleared(self):
        associate = self.make(expiry=date(2026, 9, 1))
        self.notify()
        associate.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(associate.health_certificate_file)
        self.assertIsNone(associate.health_certificate_expiry_date)
        self.assertFalse(associate.health_certificate_reminder_sent)

    def test_expiring_today_is_not_expired(self):
        associate = self.make(expiry=self.today)
        self.notify()
        associate.refresh_from_db()
        self.assertTrue(associate.health_certificate_file)
        self.assertEqual(associate.health_certificate_expiry_date, self.today)

    def test_expired_certificate_is_not_cleared_twice(self):
        associate = self.make(expiry=date(2026, 9, 1))
        self.notify()
        self.notify()
        self.assertEqual(len(mail.outbox), 1)

    def test_ignores_members_not_in_a_certification_required_activity(self):
        associate = _make_associate()
        associate.health_certificate_file = "health_certificates/cert.pdf"
        associate.health_certificate_expiry_date = date(2026, 9, 1)
        associate.save()
        course = Article.objects.create(name="Corso Sci", price=100, type="course")
        Subscription.objects.create(article=course, associate=associate, season=self.today)
        self.notify()
        associate.refresh_from_db()
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(associate.health_certificate_file)

    def test_skips_members_with_no_reachable_address(self):
        associate = self.make(expiry=date(2026, 9, 1), email=None, parent_email=None)
        output = self.notify()
        associate.refresh_from_db()
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("skipped", output)
        # Nothing was emailed, so nothing is cleared either.
        self.assertTrue(associate.health_certificate_file)

    def test_emails_the_parent_of_a_minor(self):
        associate = self.make(
            expiry=date(2026, 9, 1),
            birth_date=date(2016, 1, 1),
            parent_email="parent@example.com",
        )
        self.notify()
        associate.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("parent@example.com", mail.outbox[0].to)
        self.assertFalse(associate.health_certificate_file)

    def test_dry_run_sends_and_writes_nothing(self):
        associate = self.make(expiry=date(2026, 9, 1))
        other = self.make(expiry=date(2026, 10, 10))
        output = self.notify(dry_run=True)
        associate.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("DRY RUN", output)
        self.assertTrue(associate.health_certificate_file)
        self.assertEqual(associate.health_certificate_expiry_date, date(2026, 9, 1))
        self.assertFalse(other.health_certificate_reminder_sent)

    def test_is_idempotent(self):
        self.make(expiry=date(2026, 9, 1))
        self.notify()
        output = self.notify()
        self.assertIn("Sent 0 expiry reminder(s) and 0 expired notification(s).", output)

    def test_reports_counts(self):
        self.make(expiry=date(2026, 10, 10))
        self.make(expiry=date(2026, 10, 12))
        self.make(expiry=date(2026, 8, 1))
        output = self.notify()
        self.assertIn("Sent 2 expiry reminder(s) and 1 expired notification(s).", output)
        self.assertEqual(len(mail.outbox), 3)

    def test_warn_days_setting_changes_the_window(self):
        Settings.objects.filter(key="health_certificate_warn_days").update(value="60")
        # 46 days out: inside a 60-day window but outside the default 15.
        self.make(expiry=date(2026, 11, 20))
        self.notify()
        self.assertEqual(len(mail.outbox), 1)

    def test_one_failure_does_not_abort_the_run(self):
        good = self.make(expiry=date(2026, 9, 1))
        bad = self.make(expiry=date(2026, 9, 2))

        from unittest import mock

        original = "apps.associates.management.commands.notify_health_certificate_expiry.send_health_certificate_expiry_email"

        def flaky(associate, days_left):
            if associate.pk == bad.pk:
                raise OSError("smtp down")
            mail.EmailMultiAlternatives("ok", "ok", to=[associate.email]).send()

        with mock.patch(original, flaky):
            self.notify()

        bad.refresh_from_db()
        good.refresh_from_db()
        # The failure must not stop the healthy member from being processed.
        self.assertEqual(mail.outbox[0].to, [good.email])
        self.assertFalse(good.health_certificate_file)
        # ...and the failed one keeps its certificate so it is retried tomorrow.
        self.assertTrue(bad.health_certificate_file)