from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.associates.models import Associate


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


class DeactivateExpiredMembershipsTests(TestCase):
    today = date(2026, 9, 1)

    def make(self, expiration, active=True, card_sent=True):
        associate = _make_associate()
        # `save()` only recomputes expiration on creation, so this sticks.
        associate.expiration_date = expiration
        associate.active = active
        associate.card_sent = card_sent
        associate.save(update_fields=["expiration_date", "active", "card_sent"])
        return associate

    def deactivate(self, **options):
        out = StringIO()
        call_command("deactivate_expired_memberships", stdout=out, **options)
        return out.getvalue()

    def test_deactivates_expired_active_memberships(self):
        associate = self.make(date(2026, 8, 31))
        self.deactivate(today=self.today)
        associate.refresh_from_db()
        self.assertFalse(associate.active)

    def test_resets_card_sent_so_the_new_season_reruns_the_card(self):
        associate = self.make(date(2026, 8, 31), card_sent=True)
        self.deactivate(today=self.today)
        associate.refresh_from_db()
        self.assertFalse(associate.card_sent)

    def test_membership_expiring_today_stays_active(self):
        associate = self.make(self.today)
        self.deactivate(today=self.today)
        associate.refresh_from_db()
        self.assertTrue(associate.active)
        self.assertTrue(associate.card_sent)

    def test_future_memberships_are_untouched(self):
        associate = self.make(date(2027, 8, 31))
        self.deactivate(today=self.today)
        associate.refresh_from_db()
        self.assertTrue(associate.active)

    def test_already_inactive_memberships_are_untouched(self):
        associate = self.make(date(2026, 8, 31), active=False, card_sent=True)
        self.deactivate(today=self.today)
        associate.refresh_from_db()
        self.assertFalse(associate.active)
        self.assertTrue(associate.card_sent)

    def test_dry_run_writes_nothing(self):
        associate = self.make(date(2026, 8, 31))
        output = self.deactivate(today=self.today, dry_run=True)
        associate.refresh_from_db()
        self.assertTrue(associate.active)
        self.assertTrue(associate.card_sent)
        self.assertIn("DRY RUN", output)

    def test_is_idempotent(self):
        self.make(date(2026, 8, 31))
        self.deactivate(today=self.today)
        self.assertIn("Deactivated 0", self.deactivate(today=self.today))

    def test_reports_the_number_deactivated(self):
        self.make(date(2026, 8, 31))
        self.make(date(2026, 8, 31))
        self.assertIn("Deactivated 2", self.deactivate(today=self.today))
