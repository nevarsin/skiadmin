from django import forms
from .models import Subscription
from django.utils.translation import gettext as _

class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['season', 'certification_exp_date', 'certification_file']

        widgets = {
            'certification_exp_date': forms.DateInput(attrs={'class': 'form-control','type': 'date', 'autoclose': True }),
            'season': forms.DateInput(attrs={'class': 'form-control','type': 'date', 'autoclose': True }),
        }

        

        