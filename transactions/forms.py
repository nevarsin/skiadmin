from django import forms
from django.forms import inlineformset_factory
from .models import Transaction, TransactionLine
from associates.models import Associate
from django.utils.translation import gettext as _
from django_select2 import forms as s2forms

class AssociateWidget(s2forms.ModelSelect2Widget):
    empty_label = "-- select book --"
    model = Associate
    search_fields = ["first_name__icontains", "last_name__icontains"]
    queryset = Associate.objects.all()
    attr = {"data-minimum-input-length": 0}
        

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['associate', 'amount']        
        widgets = {
            'amount': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),                       
            "associate": AssociateWidget
        }

class TransactionLineForm(forms.ModelForm):
    class Meta:
        model = TransactionLine
        fields = ['associate', 'article', 'price']

        widgets = {
            "associate": AssociateWidget
        }

TransactionLineFormSet = inlineformset_factory(
    Transaction, TransactionLine,
    form=TransactionLineForm,
    extra=1,
    can_delete=True
)
