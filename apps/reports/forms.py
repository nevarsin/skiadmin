from django import forms
from django.db.models import DateField
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.transactions.models import Transaction
from apps.warehouse.models import SkipassUsage


class ReportTypeForm(forms.Form):
    REPORT_CHOICES = [
        ('associate', _('Associates')),
        ('transaction', _('Transactions')),
        ('subscription', _('Subscriptions')),
        ('skipass', _('Skipass')),
    ]
    report_type = forms.ChoiceField(choices=REPORT_CHOICES, label=_("Report Type"))

class AssociateReportForm(forms.Form):
    active_only = forms.BooleanField(required=False, label=_("Active Members Only"))

class SubscriptionReportForm(forms.Form):
    """Who is subscribed to an article, and who is actually compliant.

    Answers the question the club kept hitting: of the people signed up for
    gymnastics this season, how many actually handed in a medical certificate?
    """

    article = forms.ModelChoiceField(
        queryset=Article.objects.filter(active=True).order_by("name"),
        label=_("Article"),
        help_text=_("Members subscribed to this article, with their certificate status."),
    )
    non_compliant_only = forms.BooleanField(
        required=False,
        label=_("Only show members who need a certificate"),
        help_text=_("Hides the members whose certificate is still valid."),
    )

class TransactionReportForm(forms.Form):    
    date = forms.ChoiceField(choices=[], required=True, label=_("Transaction Date"))
    widgets = {
        'date': forms.DateInput(attrs={'class': 'form-control','type': 'date', 'autoclose': True }),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cast datetime to date, get distinct values
        dates = (
            Transaction.objects
            .annotate(day=Cast('date', DateField()))
            .values_list('day', flat=True)
            .distinct()
            .order_by('-day')
        )
        self.fields['date'].choices = [(d, d.strftime("%d/%m/%Y")) for d in dates]
    

class SkipassReportForm(forms.Form):
    date = forms.ChoiceField(choices=[], required=True, label=_("Ski day"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dates = (
            SkipassUsage.objects
            .values_list('date', flat=True)
            .distinct()
            .order_by('-date')
        )
        self.fields['date'].choices = [(d, d.strftime("%d/%m/%Y")) for d in dates]
    
