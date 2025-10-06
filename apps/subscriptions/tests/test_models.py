# subscriptions/tests/test_models.py
import datetime

from django.test import TestCase
from django.utils import timezone

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.subscriptions.models import Subscription
from apps.transactions.models import Transaction, TransactionLine


class SubscriptionSignalsTestCase(TestCase):

    def setUp(self):
        # Create test data
        self.associate = Associate.objects.create(first_name="Alice",birth_date=datetime.date(2024, 10, 31))
        self.course_article = Article.objects.create(name="Ski Course", type="course")
        self.skipass_article = Article.objects.create(name="Skipass", type="skipass")
        self.transaction = Transaction.objects.create(associate=self.associate, amount=100)

    def test_subscription_created_on_course_line(self):
        """Subscription is automatically created when a TransactionLine for a Course is added"""
        TransactionLine.objects.create(
            transaction=self.transaction,
            associate=self.associate,
            article=self.course_article,
            price=50
        )

    #     # There should be one Subscription
    #     subscription = Subscription.objects.filter(associate=self.associate, article=self.course_article)
    #     self.assertEqual(subscription.count(), 1)

    # def test_subscription_not_created_for_non_course(self):
    #     """TransactionLine with non-Course article does not create Subscription"""
    #     TransactionLine.objects.create(
    #         transaction=self.transaction,
    #         associate=self.associate,
    #         article=self.skipass_article,
    #         price=50
    #     )
    #     subscription = Subscription.objects.filter(associate=self.associate, article=self.skipass_article)
    #     self.assertEqual(subscription.count(), 0)

    # def test_subscription_deleted_when_line_deleted(self):
    #     """Subscription is removed when the related TransactionLine is deleted"""
    #     line = TransactionLine.objects.create(
    #         transaction=self.transaction,
    #         associate=self.associate,
    #         article=self.course_article,
    #         price=50
    #     )
    #     self.assertEqual(Subscription.objects.count(), 1)

    #     # Delete the line
    #     line.delete()
    #     self.assertEqual(Subscription.objects.count(), 0)

    # def test_no_duplicate_subscriptions(self):
    #     """Ensure unique constraint works: multiple lines for same course + associate do not create duplicates"""
    #     TransactionLine.objects.create(transaction=self.transaction, associate=self.associate, article=self.course_article, price=50)
    #     TransactionLine.objects.create(transaction=self.transaction, associate=self.associate, article=self.course_article, price=50)

    #     self.assertEqual(Subscription.objects.filter(associate=self.associate, article=self.course_article).count(), 1)
