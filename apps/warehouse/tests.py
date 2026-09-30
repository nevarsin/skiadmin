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


def _tessera_articles():
    """The TransactionLine signal unconditionally looks these up by name."""
    Article.objects.create(name="Tessera 2025/2026", price=15, category="membership")
    Article.objects.create(name="Tessera ragazzi 2025/2026", price=10, category="membership")


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
        _tessera_articles()
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
        _tessera_articles()
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
        _tessera_articles()
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
        self.assertEqual(response.context["pending_count"], 3)

    def test_plan_prechecks_every_associate_with_stock(self):
        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        for associate in (self.alice, self.bob, self.dana):
            self.assertContains(response, f'name="include_{associate.pk}" checked')

    def test_fully_consumed_associate_is_not_checkable(self):
        # bob owns a single skipass, so after one ski day he is out
        data = {"date": self.SKI_DAY.isoformat(), f"include_{self.bob.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        self.assertNotContains(response, f'name="include_{self.bob.pk}"')
        self.assertContains(response, f'name="include_{self.alice.pk}" checked')

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

    def test_confirm_creates_one_usage_per_checked_associate(self):
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

    def test_confirming_twice_does_not_duplicate(self):
        data = {"date": self.SKI_DAY.isoformat(), f"include_{self.alice.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        self.client.post(reverse("warehouse_plan"), data)
        self.assertEqual(SkipassUsage.objects.filter(associate=self.alice).count(), 1)

    def test_fully_consumed_associate_cannot_be_confirmed_again(self):
        data = {"date": self.SKI_DAY.isoformat(), f"include_{self.bob.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        next_day = date(2026, 1, 18)
        data = {"date": next_day.isoformat(), f"include_{self.bob.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        self.assertEqual(SkipassUsage.objects.filter(associate=self.bob).count(), 1)
        self.assertEqual(
            next(r for r in skipass_stock() if r.associate == self.bob).remaining, 0
        )

    def test_plan_shows_confirmed_list_after_confirmation(self):
        data = {"date": self.SKI_DAY.isoformat(), f"include_{self.alice.pk}": "on"}
        self.client.post(reverse("warehouse_plan"), data)
        response = self.client.get(reverse("warehouse_plan"), {"date": self.SKI_DAY.isoformat()})
        articles = [str(article) for article, _rows in response.context["consumed_sections"]]
        self.assertEqual(articles, ["Skipass Adulti"])
        self.assertContains(response, reverse("warehouse_undo", args=[self.SKI_DAY.isoformat()]))


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND, ALLOWED_HOSTS=["testserver", "localhost"])
class WarehouseUndoViewTests(TestCase):

    SKI_DAY = date(2026, 1, 11)

    @classmethod
    def setUpTestData(cls):
        _tessera_articles()
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
        _tessera_articles()
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
