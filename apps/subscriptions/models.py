import os

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.transactions.models import Transaction, TransactionLine

# Util functions

def subscription_certification_upload_to(instance, filename):
    # Format date like YYYYMMDD
    today_str = timezone.now().strftime("%Y%m%d")

    # Build filename components from the instance
    associate_name = f"{instance.associate.first_name}_{instance.associate.last_name}" # assuming associate has a 'name'
    exp_date = instance.certification_exp_date.strftime("%Y%m%d") if instance.certification_exp_date else "noexp"

    # Always force .pdf (or preserve extension if you want)
    ext = os.path.splitext(filename)[1] or ".pdf"

    # Final filename
    new_filename = f"Certification_{associate_name}_{exp_date}{ext}"

    # Put it under MEDIA_ROOT/subscription_certifications/<today_str>/
    return os.path.join("subscription_certifications", today_str, new_filename)

# Create your models here.

class Subscription(models.Model):
    
    article = models.ForeignKey(Article, related_name="article_subscription", on_delete=models.SET_NULL, null=True)
    associate = models.ForeignKey(Associate, related_name="associate_subscription", on_delete=models.SET_NULL, null=True)
    transaction = models.ForeignKey(Transaction, related_name="transaction_subscription", on_delete=models.SET_NULL, null=True)
    transaction_line = models.ForeignKey(TransactionLine, related_name="transactionline_subscription", on_delete=models.SET_NULL, null=True)
    season = models.DateField()
    certification_exp_date = models.DateField(null=True, blank=True)
    certification_file = models.FileField(upload_to=subscription_certification_upload_to,null=True, blank=True)
    
    def __str__(self):
        return f"{self.associate} {self.article}"    


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["associate", "article"], name="unique_subscription_per_associate_article")
        ]