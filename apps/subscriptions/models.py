from django.db import models

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.transactions.models import Transaction, TransactionLine

# Create your models here.

class Subscription(models.Model):
    
    article = models.ForeignKey(Article, related_name="article_subscription", on_delete=models.SET_NULL, null=True)
    associate = models.ForeignKey(Associate, related_name="associate_subscription", on_delete=models.SET_NULL, null=True)
    transaction = models.ForeignKey(Transaction, related_name="transaction_subscription", on_delete=models.SET_NULL, null=True)
    transaction_line = models.ForeignKey(TransactionLine, related_name="transactionline_subscription", on_delete=models.SET_NULL, null=True)
    season = models.DateField()

    def __str__(self):
        return f"{self.associate} {self.article}"    


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["associate", "article"], name="unique_subscription_per_associate_article")
        ]