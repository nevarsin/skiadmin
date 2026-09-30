from django import forms
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext as _
from django_select2 import forms as s2forms

from apps.associates.models import Associate
from apps.articles.models import Article
from apps.subscriptions.models import Subscription

from .models import Transaction, TransactionLine


class AssociateWidget(s2forms.ModelSelect2Widget):
    empty_label = "---------"
    model = Associate
    search_fields = ["first_name__icontains", "last_name__icontains"]
    queryset = Associate.objects.all()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # AJAX-backed selects hardcode a 2 character threshold; the associate
        # list is short enough to browse from the first keystroke.
        self.attrs["data-minimum-input-length"] = 0
        

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
        # line_total is derived in TransactionLine.save(); it is never posted.
        fields = ['associate', 'article', 'quantity', 'price']

        widgets = {
            "associate": AssociateWidget
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["article"].queryset = Article.objects.filter(active=True).order_by("name")

class TransactionLineInlineFormSet(BaseInlineFormSet):
    """Treat completely blank rows as deleted so unused extra lines don't fail validation."""

    _EMPTY_FIELDS = ("associate", "article", "quantity", "price")

    #: Duplicate-subscription messages raised by clean(), for the view to surface.
    duplicate_errors = []

    def _should_delete_form(self, form):
        if super()._should_delete_form(form):
            return True
        if not form.is_bound:
            return False
        return all(
            not form.data.get(form.add_prefix(name))
            for name in self._EMPTY_FIELDS
        )

    def clean(self):
        super().clean()
        self.duplicate_errors = []
        if any(self.errors):
            return

        # unique_subscription_per_associate_article allows a single subscription per
        # (associate, course) pair, so a second one can never be recorded.
        seen = {}
        for index, form in enumerate(self.forms):
            if self._should_delete_form(form):
                continue
            associate = form.cleaned_data.get("associate")
            article = form.cleaned_data.get("article")
            if not associate or not article or article.type != "course":
                continue

            if (associate.pk, article.pk) in seen:
                other = seen[(associate.pk, article.pk)]
                message = _(
                    "%(associate)s already has a subscription for %(article)s on this "
                    "transaction (lines %(first)d and %(second)d). Only one is allowed."
                ) % {
                    "associate": form.cleaned_data["associate"],
                    "article": article,
                    "first": other + 1,
                    "second": index + 1,
                }
                form.add_error("article", message)
                self.forms[other].add_error("article", message)
                self.duplicate_errors.append(message)
                continue

            # A subscription already held by a different line would collide too,
            # unless this very line is the one that owns it.
            existing = Subscription.objects.filter(
                associate_id=associate.pk, article_id=article.pk
            )
            if form.instance.pk:
                existing = existing.exclude(transaction_line_id=form.instance.pk)
            if existing.exists():
                message = _(
                    "%(associate)s already has a subscription for %(article)s."
                ) % {
                    "associate": form.cleaned_data["associate"],
                    "article": article,
                }
                form.add_error("article", message)
                self.duplicate_errors.append(message)

            seen[(associate.pk, article.pk)] = index

TransactionLineFormSet = inlineformset_factory(
    Transaction, TransactionLine,
    form=TransactionLineForm,
    formset=TransactionLineInlineFormSet,
    extra=2,
    can_delete=True
)
