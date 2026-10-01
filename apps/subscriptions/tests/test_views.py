import datetime

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.subscriptions.models import Subscription


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class SubscriptionViewsTests(TestCase):
    def setUp(self):
        self.associate = Associate.objects.create(
            first_name="Alice",
            last_name="Smith",
            birth_date=datetime.date(1990, 10, 31),
            active=True,
        )
        self.article = Article.objects.create(name="Presciistica", price=50, type="course")
        self.subscription = Subscription.objects.create(
            article=self.article,
            associate=self.associate,
            season=datetime.date(2026, 9, 1),
        )

    def test_list_subscriptions_view(self):
        response = self.client.get(reverse("list_subscriptions"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice")

    def test_list_shows_the_format_season(self):
        response = self.client.get(reverse("list_subscriptions"))
        # Iterate rather than .get(): get() clones the queryset and re-queries,
        # which would hand back instances the view never decorated.
        subscription = next(
            s for s in response.context["subscriptions"] if s.pk == self.subscription.pk
        )
        self.assertEqual(subscription.display_season, "2026/2027")

    def test_list_no_longer_shows_medical_certificate_columns(self):
        """Certificates moved to the Associate page."""
        response = self.client.get(reverse("list_subscriptions"))
        html = response.content.decode()
        self.assertNotIn("Medical cert.", html)
        self.assertNotIn("certification_file", html)

    def test_add_subscription_view(self):
        response = self.client.post(
            reverse("add_subscription"),
            {"associate": self.associate.pk, "season": "2026-09-01"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Subscription.objects.count(), 2)

    def test_add_subscription_form_defaults_the_season(self):
        response = self.client.get(reverse("add_subscription"))
        self.assertEqual(
            response.context["form"].initial["season"], timezone.localdate()
        )

    def test_edit_subscription_view(self):
        response = self.client.post(
            reverse("edit_subscription", args=[self.subscription.pk]),
            {"associate": self.associate.pk, "season": "2026-09-01"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Subscription.objects.count(), 1)

    def test_delete_subscription_view(self):
        response = self.client.post(
            reverse("delete_subscription", args=[self.subscription.pk]), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Subscription.objects.filter(pk=self.subscription.pk).exists())