from datetime import date

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.articles.models import Article
from apps.transactions.models import Transaction, TransactionLine


@receiver(post_save, sender=TransactionLine)
def create_membership_renewal(sender, instance, created, **kwargs):
    """
    Handle creation and updates of TransactionLines related to Course articles.
    """
    associate = instance.associate
    membership_article = Article.objects.filter(name='Tessera 2025/2026')[0]

    if created:
        # Case 1: Newly created line → create subscription if Course
        if (associate.active == False):
            TransactionLine.objects.get_or_create(
                article=membership_article,
                associate=associate,
                transaction=instance.transaction,
                price=membership_article.price,
            )

            # Compute next August 31st
            today = date.today()
            current_year_aug31 = date(today.year, 8, 31)
            if today > current_year_aug31:
                expiration = date(today.year + 1, 8, 31)
            else:
                expiration = current_year_aug31
            
            associate.active = True
            associate.expiration_date = expiration
            associate.save(update_fields=["active", "expiration_date"])
            
    