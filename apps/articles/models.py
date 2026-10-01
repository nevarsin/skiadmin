from django.db import models
from django.utils.translation import gettext_lazy as _

# Members up to this age get the minor membership fee article instead of the
# standard one. A stable business constant, not per-season data.
MINOR_MEMBERSHIP_MAX_AGE = 14


class Article(models.Model):
    ARTICLE_TYPES = [
        ('course', _('Course')),  # ('value', 'Display Name')
        ('single', _('Single')),        
    ]

    ARTICLE_CATEGORIES = [
        ('gymnastics', _('Gymnastics')),  # ('value', 'Display Name')
        ('skischool', _('Ski school')),
        ('membership', _('Membership fee')),
        ('tripfee', _('Trip fee')),
        ('discount', _('Discount')),
        ('skipass', _('Skipass')),
    ]

    name = models.CharField(_("Name"),max_length=100)  # Product name    
    price = models.DecimalField(_("Price"),decimal_places=2, max_digits=5)  # Product price
    active = models.BooleanField(_("Active"),default=True)  # Whether the membership card was sent
    certification_required = models.BooleanField(_("Medical cert. req."),default=False)  # Whether the membership card was sent
    is_current_membership_fee = models.BooleanField(
        _("Current membership fee"),
        default=False,
        help_text=_("Auto-added to a transaction when an inactive associate buys something. Only one article may carry this flag."),
    )
    is_current_minor_membership_fee = models.BooleanField(
        _("Current membership fee (kids)"),
        default=False,
        help_text=_("Auto-added instead of the one above for members aged %d or under. Only one article may carry this flag.") % MINOR_MEMBERSHIP_MAX_AGE,
    )

    category = models.CharField(_("Category"),choices=ARTICLE_CATEGORIES,default="membership",max_length=20)
    type = models.CharField(_("Type"),choices=ARTICLE_TYPES,default="single",max_length=20)
    
    def __str__(self):
        return f"{self.name}"    

