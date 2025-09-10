import datetime
from django.test import TestCase
from django.urls import reverse
from associates.models import Associate


class AssociateViewsTests(TestCase):
    def setUp(self):
        self.associate = Associate.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            membership_number="54321",
            expiration_date=datetime.date(2025, 8, 31),
            address_street="Street",
            address_number="1",
            address_city="City",
            address_zip="12345",
            address_province="Province",
            address_country="Country",
            birth_date=datetime.date(1995, 1, 1),
            birth_city="Town",
            birth_province="Province",
            birth_country="Country",
            fiscal_code="FISCAL456",
            parent_email="parent@example.com",
        )

    def test_list_associates_view(self):
        url = reverse("list_associates")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jane")

    def test_add_associate_view(self):
        url = reverse("add_associates")
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "membership_type": "standard",
            "expiration_date": "2025-08-31",
            "address_street": "Street",
            "address_number": "1",
            "address_city": "City",
            "address_zip": "12345",
            "address_province": "Province",
            "address_country": "Country",
            "birth_date": "2000-01-01",
            "birth_city": "Town",
            "birth_province": "Province",
            "birth_country": "Country",
            "fiscal_code": "FISCAL123",
            "parent_email": "parent@example.com",
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Associate.objects.filter(email="john@example.com").exists())

    def test_edit_associate_view(self):
        url = reverse("edit_associates", args=[self.associate.pk])
        response = self.client.post(
            url,
            {
                "first_name": "Janet",
                "last_name": "Doe",
                "email": "jane@example.com",
                "membership_number": "54321",
                "expiration_date": "2025-08-31",
                "address_street": "Street",
                "address_number": "1",
                "address_city": "City",
                "address_zip": "12345",
                "address_province": "Province",
                "address_country": "Country",
                "birth_date": "1995-01-01",
                "birth_city": "Town",
                "birth_province": "Province",
                "birth_country": "Country",
                "fiscal_code": "FISCAL456",
                "parent_email": "parent@example.com",
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 200)
        self.associate.refresh_from_db()
        self.assertEqual(self.associate.first_name, "Janet")

    def test_delete_associate_view(self):
        url = reverse("delete_associates", args=[self.associate.pk])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Associate.objects.filter(pk=self.associate.pk).exists())
