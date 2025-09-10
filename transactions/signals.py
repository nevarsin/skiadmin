from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from transactions.models import TransactionLine, Transaction
from articles.models import Article


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
            
            associate.active = True
            associate.save(update_fields=["active"])
            
    