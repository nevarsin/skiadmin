from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from subscriptions.models import Subscription
from transactions.models import TransactionLine


@receiver(post_save, sender=TransactionLine)
def create_or_update_subscription(sender, instance, created, **kwargs):
    """
    Handle creation and updates of TransactionLines related to Course articles.
    """
    article = instance.article    

    if not article:
        return

    if created:
        # Case 1: Newly created line → create subscription if Course
        if article.type == "course":
            Subscription.objects.get_or_create(
                article=article,
                associate=instance.associate,
                defaults={
                    "transaction": instance.transaction,
                    "transaction_line": instance,
                    "season": instance.transaction.date,
                    "certification_exp_date": None,
                },
            )
    else:
        # Case 2: Updated line → handle article/associate changes
        if Subscription.objects.filter(transaction_line=instance).exists():
            sub = Subscription.objects.filter(transaction_line=instance)[0]
            # If article or associate changed, check old subscription
            if (sub.article != instance.article) or (sub.associate != instance.associate):            
                # Remove old subscription if no other lines justify it
                if instance.article.type == "course":
                    Subscription.objects.filter(
                        transaction_line=instance                    
                    ).update(article=instance.article, associate=instance.associate)

                else:
                    Subscription.objects.filter(
                        transaction_line=instance                       
                    ).delete()
        else:
            # Add new subscription if needed
            if article.type == "course":
                Subscription.objects.get_or_create(
                    article=article,
                    associate=instance.associate,
                    defaults={
                        "transaction": instance.transaction,
                        "season": instance.transaction.date,
                        "certification_exp_date": None,
                    },
                )


@receiver(post_delete, sender=TransactionLine)
def delete_subscription_for_course(sender, instance, **kwargs):
    """
    Delete Subscription when a TransactionLine for a Course article is removed,
    unless another line still references it.
    """
    article = instance.article
    if not article or article.type != "course":
        return

    still_exists = TransactionLine.objects.filter(
        article=article,
        associate=instance.associate,
    ).exists()

    if not still_exists:
        Subscription.objects.filter(
            article=article,
            associate=instance.associate,
        ).delete()
