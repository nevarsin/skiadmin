from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.articles.forms import ArticleForm
from apps.articles.models import Article


def _make_minor_holder():
    return Article.objects.create(
        name="Membership kids", price=10, category="membership",
        is_current_minor_membership_fee=True,
    )


class ArticleViewsTests(TestCase):
    def setUp(self):
        self.active_article = Article.objects.create(
            name="Skipass Adulti",
            price=Decimal("250.00"),
            active=True,
        )
        self.inactive_article = Article.objects.create(
            name="Corso Sci Alpino",
            price=Decimal("120.00"),
            active=False,
        )

    def test_list_articles_hides_inactive_by_default(self):
        response = self.client.get(reverse("list_articles"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skipass Adulti")
        self.assertNotContains(response, "Corso Sci Alpino")
        self.assertEqual(len(response.context["articles"]), 1)
        self.assertEqual(response.context["articles_count"], 1)
        self.assertEqual(response.context["total_count"], 2)
        self.assertTrue(response.context["is_filtered"])
        self.assertContains(response, "1 of 2 article")

    def test_list_articles_show_all_includes_inactive(self):
        response = self.client.get(reverse("list_articles"), {"show_all": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skipass Adulti")
        self.assertContains(response, "Corso Sci Alpino")
        self.assertEqual(len(response.context["articles"]), 2)
        self.assertEqual(response.context["articles_count"], 2)
        self.assertFalse(response.context["is_filtered"])
        self.assertContains(response, "2 articles")

    def test_list_articles_can_return_nothing(self):
        self.active_article.active = False
        self.active_article.save()
        response = self.client.get(reverse("list_articles"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["articles_count"], 0)
        self.assertContains(response, "No articles found.")
        self.assertContains(response, "0 of 2 article")

    def test_list_articles_show_all_toggle_round_trips(self):
        url = reverse("list_articles")
        checked = 'name="show_all" value="1" checked'

        response = self.client.get(url, {"show_all": "1"})
        self.assertIn(checked, self.normalized_html(response))

        response = self.client.get(url)
        self.assertNotIn(checked, self.normalized_html(response))
        self.assertIn('name="show_all" value="1"', self.normalized_html(response))

    @staticmethod
    def normalized_html(response):
        return " ".join(response.content.decode().split())


class ArticleFormMembershipFlagTests(TestCase):
    """The signal resolves the flagged article with .first(), so two flags would
    silently pick the older row. The form is where that clash has to be caught."""

    def setUp(self):
        self.current = Article.objects.create(
            name="Membership", price=15, category="membership",
            is_current_membership_fee=True,
        )
        self.rival = Article.objects.create(
            name="Membership 2027/2028", price=16, category="membership",
        )

    def _form(self, **overrides):
        data = {"name": "Membership 2027/2028", "price": "16.00",
                "category": "membership", "type": "single"}
        data.update(overrides)
        return ArticleForm(data)

    def test_flagging_a_second_current_article_is_rejected(self):
        form = self._form(is_current_membership_fee=True)
        self.assertFalse(form.is_valid())
        self.assertIn("is_current_membership_fee", form.errors)

    def test_the_error_names_the_article_already_flagged(self):
        form = self._form(is_current_membership_fee=True)
        form.is_valid()
        self.assertIn("Membership", form.errors["is_current_membership_fee"][0])

    def test_minor_flag_is_guarded_independently(self):
        _make_minor_holder()
        form = self._form(is_current_minor_membership_fee=True)
        self.assertFalse(form.is_valid())
        self.assertIn("is_current_minor_membership_fee", form.errors)

    def test_the_two_flags_are_independent_slots(self):
        """The standard flag being taken must not block a different article from
        holding the minor one -- they are two elections, not one."""
        form = self._form(is_current_minor_membership_fee=True)
        self.assertTrue(form.is_valid(), form.errors)
        self.rival.is_current_minor_membership_fee = True
        self.rival.save()
        self.rival.refresh_from_db()
        self.assertTrue(self.rival.is_current_minor_membership_fee)
        self.assertFalse(self.rival.is_current_membership_fee)
        self.assertTrue(self.current.is_current_membership_fee)

    def test_editing_the_flagged_article_itself_is_allowed(self):
        form = ArticleForm(
            {"name": "Membership", "price": "15.00", "category": "membership",
             "type": "single", "is_current_membership_fee": True},
            instance=self.current,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_unflagged_article_saves_cleanly(self):
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)

    def test_the_panel_form_exposes_both_flags(self):
        html = self.client.get(reverse("add_article")).content.decode()
        self.assertIn('name="is_current_membership_fee"', html)
        self.assertIn('name="is_current_minor_membership_fee"', html)
