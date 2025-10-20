from django.db import models
from django.utils.translation import gettext_lazy as _


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
    ]

    name = models.CharField(_("Name"),max_length=100)  # Product name    
    price = models.DecimalField(_("Price"),decimal_places=2, max_digits=5)  # Product price
    active = models.BooleanField(_("Active"),default=True)  # Whether the membership card was sent
    certification_required = models.BooleanField(_("Medical cert. req."),default=False)  # Whether the membership card was sent

    category = models.CharField(_("Category"),choices=ARTICLE_CATEGORIES,default="membership",max_length=20)
    type = models.CharField(_("Type"),choices=ARTICLE_TYPES,default="single",max_length=20)
    
    def __str__(self):
        return f"{self.name}"    

