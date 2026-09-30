import datetime

from django.test import TestCase
from django.urls import reverse

from apps.associates.models import Associate


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
        self.active_associate = Associate.objects.create(
            first_name="Mark",
            last_name="Roe",
            email="mark@example.com",
            membership_number="54322",
            active=True,
            expiration_date=datetime.date(2025, 8, 31),
            address_street="Street",
            address_number="2",
            address_city="City",
            address_zip="12345",
            address_province="Province",
            address_country="Country",
            birth_date=datetime.date(1995, 1, 1),
            birth_city="Town",
            birth_province="Province",
            birth_country="Country",
            fiscal_code="FISCAL789",
            parent_email="parent@example.com",
        )

    def test_list_associates_view(self):
        url = reverse("list_associates")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jane")

    def test_list_associates_shows_all_by_default(self):
        response = self.client.get(reverse("list_associates"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jane")
        self.assertContains(response, "Mark")
        self.assertEqual(len(response.context["associates"]), 2)
        self.assertEqual(response.context["associates_count"], 2)
        self.assertEqual(response.context["total_count"], 2)
        self.assertFalse(response.context["is_filtered"])
        self.assertContains(response, "2 associates")

    def test_list_associates_filters_active_only(self):
        response = self.client.get(reverse("list_associates"), {"active_only": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mark")
        self.assertNotContains(response, "Jane")
        self.assertEqual(
            [associate.pk for associate in response.context["associates"]],
            [self.active_associate.pk],
        )
        self.assertEqual(response.context["associates_count"], 1)
        self.assertEqual(response.context["total_count"], 2)
        self.assertTrue(response.context["is_filtered"])
        self.assertContains(response, "1 of 2 associate")

    def test_list_associates_active_only_combines_with_search(self):
        url = reverse("list_associates")
        response = self.client.get(url, {"active_only": "1", "query": "Mark"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mark")
        self.assertEqual(len(response.context["associates"]), 1)
        self.assertContains(response, "1 of 2 associate")

        # Jane is inactive, so active_only excludes her even though she matches
        # the search. Her name still shows up in the echoed `value` of the
        # search box, so assert on the queryset and the empty state instead.
        response = self.client.get(url, {"active_only": "1", "query": "Jane"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No associates found.")
        self.assertEqual(list(response.context["associates"]), [])
        self.assertEqual(response.context["associates_count"], 0)
        self.assertContains(response, "0 of 2 associate")

    def test_list_associates_active_only_toggle_round_trips(self):
        url = reverse("list_associates")
        checked = 'name="active_only" value="1" checked'

        response = self.client.get(url, {"active_only": "1"})
        self.assertIn(checked, self.normalized_html(response))

        response = self.client.get(url)
        self.assertNotIn(checked, self.normalized_html(response))
        self.assertIn('name="active_only" value="1"', self.normalized_html(response))

    @staticmethod
    def normalized_html(response):
        return " ".join(response.content.decode().split())

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
