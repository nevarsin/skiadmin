from django import forms
from django.db.models import DateField
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _

from apps.associates.models import Associate
from apps.transactions.models import Transaction


class ReportTypeForm(forms.Form):
    REPORT_CHOICES = [
        ('associate', _('Associates')),
        ('transaction', _('Transactions')),
        ('subscription', _('Subscriptions')),
    ]
    report_type = forms.ChoiceField(choices=REPORT_CHOICES, label=_("Report Type"))

class AssociateReportForm(forms.Form):
    active_only = forms.BooleanField(required=False, label=_("Active Members Only"))

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
            .order_by('day')
        )
        self.fields['date'].choices = [(d, d.strftime("%Y-%m-%d")) for d in dates]
    
