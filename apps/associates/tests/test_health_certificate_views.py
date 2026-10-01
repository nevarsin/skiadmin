from datetime import date

import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.associates.utils import health_certificate_file_name

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class HealthCertificateViewTests(TestCase):
    def setUp(self):
        # Uploads must land somewhere disposable, not in the repo's media/.
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root, True)
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

        self.associate = Associate.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            membership_number="54321",
            expiration_date=date(2027, 8, 31),
            address_street="Street",
            address_number="1",
            address_city="City",
            address_zip="12345",
            birth_date=date(1995, 1, 1),
            birth_city="Town",
            active=True,
        )

    def base_payload(self, **overrides):
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "membership_number": "54321",
            # Required by AssociateForm -- omitting it is what makes the older
            # `test_edit_associate_view` fail.
            "membership_type": "standard",
            "address_street": "Street",
            "address_number": "1",
            "address_city": "City",
            "address_zip": "12345",
            "birth_date": "1995-01-01",
            "birth_city": "Town",
            "parent_email": "parent@example.com",
        }
        data.update(overrides)
        return data

    def test_edit_form_offers_the_certificate_fields(self):
        response = self.client.get(reverse("edit_associates", args=[self.associate.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("health_certificate_file", response.context["form"].fields)
        self.assertIn("health_certificate_expiry_date", response.context["form"].fields)

    def test_reminder_flag_is_not_editable(self):
        response = self.client.get(reverse("edit_associates", args=[self.associate.pk]))
        self.assertNotIn("health_certificate_reminder_sent", response.context["form"].fields)

    def test_manage_form_is_multipart(self):
        """Without enctype the browser silently drops the upload."""
        response = self.client.get(reverse("edit_associates", args=[self.associate.pk]))
        self.assertIn("multipart/form-data", response.content.decode())

    def test_uploading_a_certificate_persists_the_file_and_expiry(self):
        upload = SimpleUploadedFile(
            "cert.pdf", b"%PDF-1.4 fake", content_type="application/pdf"
        )
        response = self.client.post(
            reverse("edit_associates", args=[self.associate.pk]),
            self.base_payload(health_certificate_expiry_date="2027-03-04", health_certificate_file=upload),
        )
        self.assertEqual(response.status_code, 302)
        self.associate.refresh_from_db()
        self.assertEqual(self.associate.health_certificate_expiry_date, date(2027, 3, 4))
        stored = health_certificate_file_name(self.associate)
        today = timezone.now().strftime("%Y%m%d")
        self.assertEqual(
            stored, f"health_certificates/{today}/HealthCertificate_Jane_Doe_20270304.pdf"
        )
        # ...and it really is on disk, under MEDIA_ROOT.
        self.assertTrue(os.path.exists(os.path.join(self.media_root, stored)))

    def test_public_registration_form_hides_the_certificate(self):
        response = self.client.get(reverse("register_associate"))
        self.assertNotIn("health_certificate_file", response.context["form"].fields)
        self.assertNotIn("health_certificate_expiry_date", response.context["form"].fields)

    def listed_associate(self, pk):
        """The instance the view decorated, not a fresh one from the queryset."""
        return next(a for a in self.client.get(reverse("list_associates")).context["associates"] if a.pk == pk)

    def test_list_shows_the_certificate_status(self):
        self.associate.health_certificate_file = "health_certificates/cert.pdf"
        self.associate.health_certificate_expiry_date = date(2027, 6, 1)
        self.associate.save()
        response = self.client.get(reverse("list_associates"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.listed_associate(self.associate.pk).cert_status, "valid")
        self.assertIn("Health certificate", response.content.decode())

    def test_list_marks_a_member_without_a_certificate_as_missing(self):
        self.assertEqual(self.listed_associate(self.associate.pk).cert_status, "missing")

    def test_list_marks_an_expired_certificate(self):
        self.associate.health_certificate_file = "health_certificates/cert.pdf"
        self.associate.health_certificate_expiry_date = date(2020, 1, 1)
        self.associate.save()
        self.assertEqual(self.listed_associate(self.associate.pk).cert_status, "expired")

    def test_list_marks_a_certificate_expiring_within_the_window(self):
        from django.utils import timezone

        self.associate.health_certificate_file = "health_certificates/cert.pdf"
        self.associate.health_certificate_expiry_date = timezone.localdate() + timezone.timedelta(days=3)
        self.associate.save()
        self.assertEqual(self.listed_associate(self.associate.pk).cert_status, "expiring")

    def test_list_columns_line_up_with_the_headers(self):
        """A header/cell mismatch would silently misalign the whole table."""
        import re

        html = self.client.get(reverse("list_associates")).content.decode()
        head = html.split("<thead")[1].split("</thead>")[0]
        body_row = html.split('id="associates-tbody"')[1].split("</tr>")[0]
        self.assertEqual(head.count("<th "), body_row.count("<td"))
        self.assertEqual(head.count("<th "), 8)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"], EMAIL_BACKEND=EMAIL_BACKEND)
class SubscriptionComplianceReportTests(TestCase):
    def setUp(self):
        self.gymnastics = Article.objects.create(
            name="Presciistica 2 giorni", price=50, category="gymnastics",
            type="course", certification_required=True,
        )
        self.ski_course = Article.objects.create(
            name="Corso Sci", price=100, type="course",
        )

        self.compliant = self.make_associate("Ada", "Lovelace")
        self.compliant.health_certificate_file = "health_certificates/ada.pdf"
        self.compliant.health_certificate_expiry_date = date(2027, 6, 1)
        self.compliant.save()

        self.non_compliant = self.make_associate("Alan", "Turing")

    def make_associate(self, first, last):
        return Associate.objects.create(
            first_name=first, last_name=last,
            email=f"{first.lower()}@example.com",
            expiration_date=date(2027, 8, 31),
            address_street="Street", address_number="1",
            address_city="City", address_zip="12345",
            birth_date=date(1990, 1, 1), birth_city="Town",
        )

    def subscribe(self, associate, article):
        from apps.subscriptions.models import Subscription

        return Subscription.objects.create(
            article=article, associate=associate, season=date(2026, 9, 1)
        )

    def test_select_report_offers_subscriptions(self):
        response = self.client.post(reverse("select_report"), {"report_type": "subscription"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["type"], "subscription")

    def test_generate_pdf(self):
        self.subscribe(self.compliant, self.gymnastics)
        self.subscribe(self.non_compliant, self.gymnastics)
        response = self.client.get(
            reverse("generate_report", args=["subscription"]), {"article": self.gymnastics.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(".pdf", response["Content-Disposition"])

    def test_unknown_article_rerenders_the_form(self):
        response = self.client.get(
            reverse("generate_report", args=["subscription"]), {"article": "999999"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.get("Content-Type", ""), "application/pdf")
        self.assertTrue(response.context["form"].errors)

    def test_missing_article_rerenders_the_form(self):
        response = self.client.get(reverse("generate_report", args=["subscription"]))
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.get("Content-Type", ""), "application/pdf")

    def test_counts_split_by_status(self):
        self.subscribe(self.compliant, self.gymnastics)
        self.subscribe(self.non_compliant, self.gymnastics)
        rows, counts = self.report_rows(self.gymnastics)
        self.assertEqual(counts, {"valid": 1, "expiring": 0, "expired": 0, "missing": 1})
        self.assertEqual(len(rows), 2)

    def test_non_compliant_only_filters_valid_members_out(self):
        self.subscribe(self.compliant, self.gymnastics)
        self.subscribe(self.non_compliant, self.gymnastics)
        rows, counts = self.report_rows(self.gymnastics, non_compliant_only=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["associate"], self.non_compliant)
        # The summary still describes everyone, not just the filtered list.
        self.assertEqual(counts, {"valid": 1, "expiring": 0, "expired": 0, "missing": 1})

    def test_cert_not_required_article_is_flagged_informational(self):
        self.subscribe(self.compliant, self.ski_course)
        response = self.client.get(
            reverse("generate_report", args=["subscription"]), {"article": self.ski_course.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["certification_required"])

    def report_rows(self, article, **params):
        """Render the PDF branch and read back the rows/counts it built."""
        params["article"] = article.pk
        response = self.client.get(reverse("generate_report", args=["subscription"]), params)
        self.assertEqual(response.status_code, 200)
        return response.context["rows"], response.context["counts"]