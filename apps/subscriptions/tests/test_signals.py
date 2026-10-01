import datetime

from django.test import TestCase

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.subscriptions.models import Subscription
from apps.transactions.models import Transaction, TransactionLine


class SubscriptionUpdateSignalsTestCase(TestCase):
    def setUp(self):
        self.associate = Associate.objects.create(
            first_name="Alice",
            birth_date=datetime.date(1990, 10, 31),
            active=True,
        )
        self.course_article = Article.objects.create(name="Ski Course", price=50, type="course")
        self.skipass_article = Article.objects.create(name="Skipass", price=200, type="single")
        self.transaction = Transaction.objects.create(associate=self.associate, amount=100)

    def test_subscription_updated_on_article_change(self):
        line = TransactionLine.objects.create(
            transaction=self.transaction, associate=self.associate,
            article=self.skipass_article, price=50, quantity=1,
        )
        self.assertEqual(Subscription.objects.count(), 0)

        # Change to course -> subscription should be created
        line.article = self.course_article
        line.save()
        self.assertEqual(Subscription.objects.count(), 1)

    def test_subscription_removed_when_line_moves_to_a_non_course(self):
        line = TransactionLine.objects.create(
            transaction=self.transaction, associate=self.associate,
            article=self.course_article, price=50, quantity=1,
        )
        self.assertEqual(Subscription.objects.count(), 1)

        line.article = self.skipass_article
        line.save()
        self.assertEqual(Subscription.objects.count(), 0)