from datetime import date

from django.test import TestCase

from apps.associates.utils import membership_expiration
from apps.core.models import Settings


class MembershipExpirationTests(TestCase):
    """The expiry policy is a site setting, so a bad value must never raise."""

    def configure(self, **values):
        for key, value in values.items():
            Settings.objects.update_or_create(key=key, defaults={"value": value})

    def test_absent_settings_fall_back_to_fixed_august_31(self):
        Settings.objects.all().delete()
        self.assertEqual(membership_expiration(date(2026, 6, 1)), date(2026, 8, 31))

    def test_fixed_on_the_boundary_stays_this_year(self):
        self.configure(membership_expiry_mode="fixed", membership_expiry_fixed_date="08-31")
        self.assertEqual(membership_expiration(date(2026, 8, 31)), date(2026, 8, 31))

    def test_fixed_after_the_boundary_rolls_to_next_year(self):
        self.configure(membership_expiry_mode="fixed", membership_expiry_fixed_date="08-31")
        self.assertEqual(membership_expiration(date(2026, 9, 1)), date(2027, 8, 31))

    def test_custom_fixed_date(self):
        self.configure(membership_expiry_mode="fixed", membership_expiry_fixed_date="12-31")
        self.assertEqual(membership_expiration(date(2026, 6, 1)), date(2026, 12, 31))
        self.assertEqual(membership_expiration(date(2027, 1, 1)), date(2027, 12, 31))

    def test_rolling_adds_years_from_the_given_date(self):
        self.configure(membership_expiry_mode="rolling", membership_expiry_rolling_years="1")
        self.assertEqual(membership_expiration(date(2026, 3, 15)), date(2027, 3, 15))

    def test_rolling_honours_the_year_count(self):
        self.configure(membership_expiry_mode="rolling", membership_expiry_rolling_years="3")
        self.assertEqual(membership_expiration(date(2026, 1, 10)), date(2029, 1, 10))

    def test_rolling_clamps_february_29(self):
        self.configure(membership_expiry_mode="rolling", membership_expiry_rolling_years="1")
        self.assertEqual(membership_expiration(date(2024, 2, 29)), date(2025, 2, 28))

    def test_fixed_leap_day_clamps_to_the_last_day_of_february(self):
        self.configure(membership_expiry_mode="fixed", membership_expiry_fixed_date="02-29")
        self.assertEqual(membership_expiration(date(2026, 1, 1)), date(2026, 2, 28))
        self.assertEqual(membership_expiration(date(2028, 1, 1)), date(2028, 2, 29))

    def test_unknown_mode_falls_back_to_fixed(self):
        self.configure(membership_expiry_mode="nonsense", membership_expiry_fixed_date="08-31")
        self.assertEqual(membership_expiration(date(2026, 6, 1)), date(2026, 8, 31))

    def test_malformed_fixed_date_falls_back_to_august_31(self):
        self.configure(membership_expiry_mode="fixed", membership_expiry_fixed_date="not-a-date")
        self.assertEqual(membership_expiration(date(2026, 6, 1)), date(2026, 8, 31))

    def test_malformed_rolling_years_fall_back_to_one(self):
        self.configure(membership_expiry_mode="rolling", membership_expiry_rolling_years="lots")
        self.assertEqual(membership_expiration(date(2026, 3, 15)), date(2027, 3, 15))
