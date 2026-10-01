from datetime import date

import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.articles.models import MINOR_MEMBERSHIP_MAX_AGE, Article
from apps.transactions.models import Transaction, TransactionLine

from apps.associates.utils import membership_expiration, send_membership_card_via_email

logger = logging.getLogger(__name__)


def _age_on(birth_date, today=None):
    """Full years elapsed between `birth_date` and `today` (default: today)."""
    today = today or date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _current_membership_article(associate):
    """The membership fee article the Articles panel designates for this associate.

    Which article that is comes from the `is_current_membership_fee` /
    `is_current_minor_membership_fee` flags, so the season's articles are chosen
    in the Articles panel instead of being hardcoded here. Returns None when
    nothing is flagged.
    """
    if _age_on(associate.birth_date) <= MINOR_MEMBERSHIP_MAX_AGE:
        return Article.objects.filter(is_current_minor_membership_fee=True).first()
    return Article.objects.filter(is_current_membership_fee=True).first()


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

    if not created or associate.active:
        return

    membership_article = _current_membership_article(associate)
    if membership_article is None:
        # No article flagged in the Articles panel: charge no fee and leave the
        # associate inactive rather than activating them for free.
        logger.warning(
            "No current membership fee article flagged for associate %s: "
            "set is_current_membership_fee (and is_current_minor_membership_fee "
            "for under-%ds) on the Articles panel.",
            associate.pk, MINOR_MEMBERSHIP_MAX_AGE,
        )
        return

    TransactionLine.objects.get_or_create(
        article=membership_article,
        associate=associate,
        transaction=instance.transaction,
        price=membership_article.price,
        line_total=membership_article.price,
        quantity=1,
    )

    associate.active = True
    associate.expiration_date = membership_expiration()
    associate.save(update_fields=["active", "expiration_date"])
    
    # Send membership card if not already sent
    if not associate.card_sent and associate.email:                
        send_membership_card_via_email(associate)
