from django import forms
from django.forms import inlineformset_factory
from .models import Transaction, TransactionLine
from django.utils.translation import gettext as _

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['associate', 'amount']
        widgets = {
            'amount': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),
        }

class TransactionLineForm(forms.ModelForm):
    class Meta:
        model = TransactionLine
        fields = ['associate', 'item_name', 'price']

TransactionLineFormSet = inlineformset_factory(
    Transaction, TransactionLine,
    form=TransactionLineForm,
    extra=1,
    can_delete=False
)
