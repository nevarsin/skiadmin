from django import forms
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext as _
from django_select2 import forms as s2forms

from apps.associates.models import Associate
from apps.articles.models import Article

from .models import Transaction, TransactionLine


class AssociateWidget(s2forms.ModelSelect2Widget):
    empty_label = "-- select book --"
    model = Associate
    search_fields = ["first_name__icontains", "last_name__icontains"]
    queryset = Associate.objects.all()
    attr = {"data-minimum-input-length": 0}
        

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['associate', 'amount', 'method']        
        widgets = {
            'amount': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),                       
            "associate": AssociateWidget
        }

class TransactionLineForm(forms.ModelForm):
    class Meta:
        model = TransactionLine
        fields = ['associate', 'article', 'quantity', 'price', 'line_total']

        widgets = {
            "associate": AssociateWidget
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["article"].queryset = Article.objects.filter(active=True).order_by("name")

class TransactionLineInlineFormSet(BaseInlineFormSet):
    """Treat completely blank rows as deleted so unused extra lines don't fail validation."""

    _EMPTY_FIELDS = ("associate", "article", "quantity", "price")

    def _should_delete_form(self, form):
        if super()._should_delete_form(form):
            return True
        if not form.is_bound:
            return False
        return all(
            not form.data.get(form.add_prefix(name))
            for name in self._EMPTY_FIELDS
        )

TransactionLineFormSet = inlineformset_factory(
    Transaction, TransactionLine,
    form=TransactionLineForm,
    formset=TransactionLineInlineFormSet,
    extra=10,
    can_delete=True
)
