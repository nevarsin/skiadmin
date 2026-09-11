from datetime import date

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.articles.models import Article
from apps.transactions.models import Transaction, TransactionLine

from apps.associates.utils import send_membership_card_via_email

@receiver(post_save, sender=TransactionLine)
def create_membership_renewal(sender, instance, created, **kwargs):
    
    # Handle Transaction post-saving logic
    associate = instance.associate
    
    # Set discounts for counselor members
    if (associate.membership_type == 'counselor' and instance.article.category != 'discount' and instance.article.category != 'membership'):        
        counselor_discount_article = Article.objects.filter(name='Sconto consigliere')[0]
        TransactionLine.objects.get_or_create(
                article=counselor_discount_article,
                associate=associate,
                transaction=instance.transaction,
                price=-instance.price / 2,
                line_total=-instance.price / 2,
                quantity=1,
            )
        
    # Check if associate is below minor threshold
    if associate.birth_date.year >= 2011:
        membership_article = Article.objects.filter(name='Tessera ragazzi 2025/2026')[0]
    else:
        membership_article = Article.objects.filter(name='Tessera 2025/2026')[0]        

    if created:
        # Case 1: Newly created line → create subscription if Course
        if (associate.active == False):
            TransactionLine.objects.get_or_create(
                article=membership_article,
                associate=associate,
                transaction=instance.transaction,
                price=membership_article.price,
                line_total=membership_article.price,
                quantity=1,
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
            
            # Send membership card if not already sent
            if not associate.card_sent and associate.email:                
                send_membership_card_via_email(associate)