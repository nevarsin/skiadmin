from django import forms
from django.utils import timezone
from django_select2 import forms as s2forms

from apps.associates.models import Associate

from .models import Subscription


class AssociateWidget(s2forms.ModelSelect2Widget):
    empty_label = "-- select associate --"
    model = Associate
    search_fields = ["first_name__icontains", "last_name__icontains"]
    queryset = Associate.objects.all()


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        # `season` is required by the model, so it has to be on the form too --
        # without it the form could never validate and saving blew up on a
        # not-null violation.
        fields = ['associate', 'season']

        widgets = {
            'season': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'autoclose': True}),
            "associate": AssociateWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Subscriptions are almost always created for the season in progress.
        if not self.initial.get("season") and not self.instance.pk:
            self.initial["season"] = timezone.localdate()