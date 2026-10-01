from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.transactions.models import Transaction, TransactionLine
from apps.warehouse.models import SkipassUsage, skipass_stock

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


def _make_associate(first_name="Test", last_name="User", **kw):
    return Associate.objects.create(
        first_name=first_name, last_name=last_name, email=f"{first_name}@example.com",
        membership_type="standard", active=True,
        birth_date=date(1990, 1, 1), birth_city="Trento", birth_country="IT",
        expiration_date=date(2026, 8, 31),
        address_street="Via Roma", address_number="1", address_city="Tarcento",
        address_zip="33018", address_country="IT", **kw,
    )


def _buy(associate, article, quantity=1):
    transaction = Transaction.objects.create(associate=associate, amount=0, method="cash")
    line = TransactionLine.objects.create(
        transaction=transaction, associate=associate, article=article,
        quantity=quantity, price=article.price, line_total=article.price * quantity,
    )
    return line


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class SkipassStockTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.skipass = Article.objects.create(name="Skipass Adulti", price=300, category="skipass")
        cls.skipass_minor = Article.objects.create(name="Skipass Ragazzi", price=200, category="skipass")
        cls.other = Article.objects.create(name="Presciistica", price=80, category="course")

        cls.alice = _make_associate("Alice")
        cls.bob = _make_associate("Bob")
        cls.carol = _make_associate("Carol")

        _buy(cls.alice, cls.skipass, quantity=6)
        _buy(cls.bob, cls.skipass_minor, quantity=3)
        _buy(cls.carol, cls.other, quantity=2)

    def _row(self, associate):
        return next(r for r in skipass_stock() if r.associate == associate)

    def test_only_skipass_articles_count(self):
        """Non-skipass purchases never appear in the warehouse."""
        ids = [row.associate.pk for row in skipass_stock()]
        self.assertIn(self.alice.pk, ids)
        self.assertIn(self.bob.pk, ids)
        self.assertNotIn(self.carol.pk, ids)

    def test_remaining_starts_at_purchased(self):
        row = self._row(self.alice)
        self.assertEqual(row.purchased, 6)
        self.assertEqual(row.consumed, 0)
        self.assertEqual(row.remaining, 6)
        self.assertEqual(row.article, self.skipass)

    def test_remaining_decreases_with_usage(self):
        SkipassUsage.objects.create(
            date=date(2026, 1, 4), associate=self.alice, article=self.skipass
        )
        row = self._row(self.alice)
        self.assertEqual(row.consumed, 1)
        self.assertEqual(row.remaining, 5)

    def test_multiple_articles_per_associate_are_summed(self):
        _buy(self.alice, self.skipass_minor, quantity=2)
        row = self._row(self.alice)
        self.assertEqual(row.purchased, 8)
        self.assertEqual(row.remaining, 8)


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class SkipassUsageConstraintTests(TestCase):

    def test_one_usage_per_associate_per_day(self):
        skipass = Article.objects.create(name="Skipass Adulti", price=300, category="skipass")
        associate = _make_associate("Alice")
        SkipassUsage.objects.create(date=date(2026, 1, 4), associate=associate, article=skipass)
        with self.assertRaises(Exception):
            SkipassUsage.objects.create(date=date(2026, 1, 4), associate=associate, article=skipass)


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class WarehousePlanViewTests(TestCase):

    SKI_DAY = date(2026, 1, 11)

    @classmethod
    def setUpTestData(cls):
        cls.skipass = Article.objects.create(name="Skipass Adulti", price=300, category="skipass")
        cls.skipass_minor = Article.objects.create(name="Skipass Ragazzi", price=200, category="skipass")

        cls.alice = _make_associate("Alice")
        cls.bob = _make_associate("Bob")
        cls.dana = _make_associate("Dana")

        _buy(cls.alice, cls.skipass, quantity=3)
        _buy(cls.bob, cls.skipass, quantity=1)
        _buy(cls.dana, cls.skipass_minor, quantity=1)

    def test_plan_lists_associates_grouped_by_article(self):
        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skipass Adulti")
        self.assertContains(response, "Skipass Ragazzi")
        self.assertEqual(len(response.context["sections"]), 2)
        self.assertEqual(response.context["editable_count"], 3)
        self.assertEqual(response.context["consumed_count"], 0)
        self.assertFalse(response.context["has_consumed"])

    def test_plan_prechecks_every_associate_with_stock(self):
        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        for associate in (self.alice, self.bob, self.dana):
            self.assertContains(response, f'name="include_{associate.pk}" checked')

    def test_associate_out_of_skipass_from_other_days_is_not_checkable(self):
        """Eve burned her only skipass on an earlier day: nothing to offer today."""
        eve = _make_associate("Eve")
        _buy(eve, self.skipass, quantity=1)
        SkipassUsage.objects.create(date=date(2026, 1, 4), associate=eve, article=self.skipass)

        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        self.assertNotContains(response, f'name="include_{eve.pk}"')
        # but she is still listed, greyed out, with her real numbers
        self.assertContains(response, "Eve")

    def test_associate_out_of_skipass_stays_undoable(self):
        """Someone who burned their last skipass today must still be uncheckable."""
        data = {"date": self.SKI_DAY.isoformat(), f"include_{self.bob.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        self.assertContains(response, f'name="include_{self.bob.pk}" checked')

    def test_plan_defaults_to_today_when_no_date_given(self):
        response = self.client.get(reverse("warehouse_plan"))
        self.assertEqual(response.status_code, 200)
        from django.utils import timezone
        self.assertEqual(response.context["date"], timezone.localdate())

    def test_plan_ignores_an_invalid_date(self):
        response = self.client.get(reverse("warehouse_plan"), {"date": "not-a-date"})
        self.assertEqual(response.status_code, 200)
        from django.utils import timezone
        self.assertEqual(response.context["date"], timezone.localdate())

    def test_save_creates_one_usage_per_checked_associate(self):
        data = {"date": self.SKI_DAY.isoformat()}
        data[f"include_{self.alice.pk}"] = "on"
        data[f"include_{self.bob.pk}"] = "on"
        # dana is left unchecked (absent)

        response = self.client.post(reverse("warehouse_plan"), data)

        self.assertRedirects(response, f"{reverse('warehouse_plan')}?date={self.SKI_DAY.isoformat()}")
        self.assertEqual(SkipassUsage.objects.count(), 2)
        usage = SkipassUsage.objects.get(associate=self.alice)
        self.assertEqual(usage.date, self.SKI_DAY)
        self.assertEqual(usage.article, self.skipass)
        self.assertEqual(usage.quantity, 1)
        self.assertFalse(SkipassUsage.objects.filter(associate=self.dana).exists())

    def test_saving_twice_does_not_duplicate(self):
        data = {"date": self.SKI_DAY.isoformat(), f"include_{self.alice.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        self.client.post(reverse("warehouse_plan"), data)
        self.assertEqual(SkipassUsage.objects.filter(associate=self.alice).count(), 1)

    def test_associate_without_stock_cannot_be_saved_again(self):
        data = {"date": self.SKI_DAY.isoformat(), f"include_{self.bob.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        next_day = date(2026, 1, 18)
        data = {"date": next_day.isoformat(), f"include_{self.bob.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        self.assertEqual(SkipassUsage.objects.filter(associate=self.bob).count(), 1)
        self.assertEqual(
            next(r for r in skipass_stock() if r.associate == self.bob).remaining, 0
        )

    def test_plan_shows_the_consumed_count_after_saving(self):
        data = {"date": self.SKI_DAY.isoformat(), f"include_{self.alice.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        self.assertEqual(response.context["consumed_count"], 1)
        self.assertTrue(response.context["has_consumed"])
        self.assertContains(response, reverse("warehouse_undo", args=[self.SKI_DAY.isoformat()]))
        # alice is now checked *because* she was consumed, not just by default
        self.assertContains(response, f'name="include_{self.alice.pk}" checked')


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class WarehouseRestoreTests(TestCase):
    """The operator realises at the end of the day that someone was absent."""

    SKI_DAY = date(2026, 1, 11)

    @classmethod
    def setUpTestData(cls):
        cls.skipass = Article.objects.create(name="Skipass Adulti", price=300, category="skipass")
        cls.alice = _make_associate("Alice")
        cls.bob = _make_associate("Bob")
        _buy(cls.alice, cls.skipass, quantity=3)
        _buy(cls.bob, cls.skipass, quantity=3)

    def _save(self, *associate_ids, confirm=False):
        data = {"date": self.SKI_DAY.isoformat()}
        for associate_id in associate_ids:
            data[f"include_{associate_id}"] = "on"
        if confirm:
            data["confirm"] = "1"
        return self.client.post(reverse("warehouse_plan"), data)

    def _confirm_both(self):
        self._save(self.alice.pk, self.bob.pk)

    def test_unchecking_an_absent_associate_asks_for_confirmation(self):
        self._confirm_both()
        response = self._save(self.alice.pk)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "warehouse/confirm_changes.html")
        # nothing has been deleted yet
        self.assertEqual(SkipassUsage.objects.count(), 2)
        self.assertContains(response, "Bob")

    def test_confirming_the_change_restores_the_skipass(self):
        self._confirm_both()
        self._save(self.alice.pk)
        response = self._save(self.alice.pk, confirm=True)

        self.assertRedirects(response, f"{reverse('warehouse_plan')}?date={self.SKI_DAY.isoformat()}")
        self.assertFalse(SkipassUsage.objects.filter(associate=self.bob).exists())
        self.assertTrue(SkipassUsage.objects.filter(associate=self.alice).exists())
        bob = next(r for r in skipass_stock() if r.associate == self.bob)
        self.assertEqual(bob.consumed, 0)
        self.assertEqual(bob.remaining, 3)

    def test_cancelling_the_confirmation_changes_nothing(self):
        self._confirm_both()
        self._save(self.alice.pk)
        self.assertEqual(SkipassUsage.objects.count(), 2)

    def test_adding_and_restoring_at_once_is_atomic(self):
        self._confirm_both()
        dana = _make_associate("Dana")
        _buy(dana, self.skipass, quantity=1)

        # alice stays, bob is given back, dana is added
        response = self._save(self.alice.pk, dana.pk)
        self.assertTemplateUsed(response, "warehouse/confirm_changes.html")
        self.assertEqual(SkipassUsage.objects.count(), 2)

        self._save(self.alice.pk, dana.pk, confirm=True)

        self.assertEqual(
            sorted(SkipassUsage.objects.values_list("associate__first_name", flat=True)),
            ["Alice", "Dana"],
        )

    def test_unchecking_everyone_clears_the_day(self):
        self._confirm_both()
        self._save()
        self._save(confirm=True)
        self.assertEqual(SkipassUsage.objects.count(), 0)

    def test_saving_without_changes_is_a_noop(self):
        self._confirm_both()
        response = self._save(self.alice.pk, self.bob.pk)
        self.assertRedirects(response, f"{reverse('warehouse_plan')}?date={self.SKI_DAY.isoformat()}")
        self.assertEqual(SkipassUsage.objects.count(), 2)

    def test_a_restored_skipass_stays_restored_after_reload(self):
        """Otherwise the next save would quietly hand the skipass back again."""
        self._confirm_both()
        self._save(self.alice.pk)
        self._save(self.alice.pk, confirm=True)

        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        # alice is still confirmed, bob is not ticked back on
        self.assertContains(response, f'name="include_{self.alice.pk}" checked')
        self.assertContains(response, f'name="include_{self.bob.pk}"')
        self.assertNotContains(response, f'name="include_{self.bob.pk}" checked')
        # and a further save does not bring him back
        self._save(self.alice.pk)
        self.assertEqual(
            sorted(SkipassUsage.objects.values_list("associate__first_name", flat=True)),
            ["Alice"],
        )

    def test_unconsumed_associates_are_unticked_once_the_day_is_confirmed(self):
        self._confirm_both()
        dana = _make_associate("Dana")
        _buy(dana, self.skipass, quantity=2)

        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        # available to tick, but not ticked by default
        self.assertContains(response, f'name="include_{dana.pk}"')
        self.assertNotContains(response, f'name="include_{dana.pk}" checked')

    def test_checked_count_reflects_the_ticked_boxes(self):
        self._confirm_both()
        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        self.assertEqual(response.context["checked_count"], 2)
        self.assertEqual(response.context["editable_count"], 2)

        # nothing confirmed yet: everybody with stock starts ticked
        SkipassUsage.objects.all().delete()
        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        self.assertEqual(response.context["checked_count"], 2)
        self.assertContains(response, "2 associates checked")


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class WarehouseUndoViewTests(TestCase):

    SKI_DAY = date(2026, 1, 11)

    @classmethod
    def setUpTestData(cls):
        cls.skipass = Article.objects.create(name="Skipass Adulti", price=300, category="skipass")
        cls.alice = _make_associate("Alice")
        cls.bob = _make_associate("Bob")
        _buy(cls.alice, cls.skipass, quantity=2)
        _buy(cls.bob, cls.skipass, quantity=2)

    def test_undo_page_lists_usages(self):
        SkipassUsage.objects.create(date=self.SKI_DAY, associate=self.alice, article=self.skipass)
        response = self.client.get(reverse("warehouse_undo", args=[self.SKI_DAY.isoformat()]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice")

    def test_undo_deletes_that_day_only(self):
        other_day = date(2026, 1, 18)
        SkipassUsage.objects.create(date=self.SKI_DAY, associate=self.alice, article=self.skipass)
        SkipassUsage.objects.create(date=self.SKI_DAY, associate=self.bob, article=self.skipass)
        SkipassUsage.objects.create(date=other_day, associate=self.alice, article=self.skipass)

        response = self.client.post(reverse("warehouse_undo", args=[self.SKI_DAY.isoformat()]))

        self.assertRedirects(response, f"{reverse('warehouse_plan')}?date={self.SKI_DAY.isoformat()}")
        self.assertEqual(SkipassUsage.objects.filter(date=self.SKI_DAY).count(), 0)
        self.assertEqual(SkipassUsage.objects.filter(date=other_day).count(), 1)


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class SkipassReportTests(TestCase):

    SKI_DAY = date(2026, 1, 11)

    @classmethod
    def setUpTestData(cls):
        cls.skipass = Article.objects.create(name="Skipass Adulti", price=300, category="skipass")
        cls.alice = _make_associate("Alice")
        _buy(cls.alice, cls.skipass, quantity=2)
        SkipassUsage.objects.create(date=cls.SKI_DAY, associate=cls.alice, article=cls.skipass)

    def test_select_report_offers_skipass(self):
        response = self.client.post(reverse("select_report"), {"report_type": "skipass"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["type"], "skipass")

    def test_generate_skipass_pdf(self):
        response = self.client.get(
            reverse("generate_report", args=["skipass"]), {"date": self.SKI_DAY.isoformat()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(".pdf", response["Content-Disposition"])

    def test_pdf_requires_a_known_date(self):
        """An unknown date re-renders the form instead of blowing up."""
        response = self.client.get(
            reverse("generate_report", args=["skipass"]), {"date": date(2030, 5, 5).isoformat()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.get("Content-Type", ""), "application/pdf")
        self.assertTrue(response.context["form"].errors)
