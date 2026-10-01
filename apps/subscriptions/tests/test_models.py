import datetime

from django.test import TestCase

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.subscriptions.models import Subscription
from apps.transactions.models import Transaction, TransactionLine


class SubscriptionSignalsTestCase(TestCase):
    def setUp(self):
        # An *active* associate keeps the membership-renewal signal out of the
        # way, so these tests never send a real membership card email.
        self.associate = Associate.objects.create(
            first_name="Alice",
            birth_date=datetime.date(1990, 10, 31),
            active=True,
        )
        self.course_article = Article.objects.create(name="Ski Course", price=50, type="course")
        self.skipass_article = Article.objects.create(name="Skipass", price=200, type="single")
        self.transaction = Transaction.objects.create(associate=self.associate, amount=100)

    def buy(self, article, quantity=1, price=50):
        return TransactionLine.objects.create(
            transaction=self.transaction,
            associate=self.associate,
            article=article,
            price=price,
            quantity=quantity,
        )

    def test_subscription_created_on_course_line(self):
        """Subscription is automatically created when a TransactionLine for a Course is added"""
        self.buy(self.course_article)
        subscription = Subscription.objects.filter(
            associate=self.associate, article=self.course_article
        )
        self.assertEqual(subscription.count(), 1)

    def test_subscription_not_created_for_non_course(self):
        """TransactionLine with non-Course article does not create Subscription"""
        self.buy(self.skipass_article)
        subscription = Subscription.objects.filter(
            associate=self.associate, article=self.skipass_article
        )
        self.assertEqual(subscription.count(), 0)

    def test_subscription_deleted_when_line_deleted(self):
        """Subscription is removed when the related TransactionLine is deleted"""
        line = self.buy(self.course_article)
        self.assertEqual(Subscription.objects.count(), 1)

        line.delete()
        self.assertEqual(Subscription.objects.count(), 0)

    def test_no_duplicate_subscriptions(self):
        """Multiple lines for the same course and associate collapse into one"""
        self.buy(self.course_article)
        self.buy(self.course_article)

        self.assertEqual(
            Subscription.objects.filter(
                associate=self.associate, article=self.course_article
            ).count(),
            1,
        )

    def test_no_health_certificate_fields_on_subscription(self):
        """Certificates moved to the Associate so they survive across trunks."""
        field_names = {field.name for field in Subscription._meta.get_fields()}
        self.assertNotIn("certification_file", field_names)
        self.assertNotIn("certification_exp_date", field_names)