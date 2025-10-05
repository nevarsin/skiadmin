from django import forms
from .models import Subscription
from django.utils.translation import gettext as _
from django_select2 import forms as s2forms
from associates.models import Associate


class AssociateWidget(s2forms.ModelSelect2Widget):
    empty_label = "-- select book --"
    model = Associate
    search_fields = ["first_name__icontains", "last_name__icontains"]
    queryset = Associate.objects.all()

class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['certification_file', 'certification_exp_date', 'associate']

        widgets = {
            'certification_exp_date': forms.DateInput(attrs={'class': 'form-control','type': 'date', 'autoclose': True }),            
            "associate": AssociateWidget,
        }

        

        