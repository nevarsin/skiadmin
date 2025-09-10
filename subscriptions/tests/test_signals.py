# subscriptions/tests/test_signals.py
from django.test import TestCase

class SubscriptionUpdateSignalsTestCase(TestCase):

    def setUp(self):
        # Similar setup as above
        ...

    def test_subscription_updated_on_article_change(self):
        line = TransactionLine.objects.create(transaction=self.transaction, associate=self.associate, article=self.skipass_article, price=50)
        self.assertEqual(Subscription.objects.count(), 0)

        # Change to course → subscription should be created
        line.article = self.course_article
        line.save()
        self.assertEqual(Subscription.objects.count(), 1)
