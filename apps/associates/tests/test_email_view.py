import datetime

from django.test import TestCase
from django.urls import reverse

from apps.associates.models import Associate


class AssociateEmailViewTests(TestCase):
    def setUp(self):
        self.associate = Associate.objects.create(
            first_name="Jane",
            last_name="Doe",
            email=None,
            membership_number="54321",
            expiration_date=datetime.date(2025, 8, 31),
            address_street="Street",
            address_number="1",
            address_city="City",
            address_zip="12345",
            birth_date=datetime.date(1995, 1, 1),
            birth_city="Town",
        )
        self.url = reverse("associate_email", args=[self.associate.pk])

    def test_get_reports_missing_email_as_empty_string(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "")
        self.assertEqual(response.json()["name"], "Jane Doe")

    def test_get_reports_existing_email(self):
        self.associate.email = "jane@example.com"
        self.associate.save()
        response = self.client.get(self.url)
        self.assertEqual(response.json()["email"], "jane@example.com")

    def test_get_unknown_associate_is_404(self):
        response = self.client.get(reverse("associate_email", args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_post_sets_email(self):
        response = self.client.post(self.url, {"email": "  jane@example.com "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "jane@example.com")
        self.associate.refresh_from_db()
        self.assertEqual(self.associate.email, "jane@example.com")

    def test_post_rejects_invalid_email(self):
        response = self.client.post(self.url, {"email": "not-an-email"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"], ["Enter a valid email address."])
        self.associate.refresh_from_db()
        self.assertIsNone(self.associate.email)

    def test_post_rejects_blank_email(self):
        response = self.client.post(self.url, {"email": "   "})
        self.assertEqual(response.status_code, 400)
        self.associate.refresh_from_db()
        self.assertIsNone(self.associate.email)

    def test_post_only_touches_email(self):
        self.associate.notes = "keep me"
        self.associate.save()
        Associate.objects.filter(pk=self.associate.pk).update(notes="changed elsewhere")
        self.client.post(self.url, {"email": "jane@example.com"})
        self.associate.refresh_from_db()
        self.assertEqual(self.associate.notes, "changed elsewhere")
