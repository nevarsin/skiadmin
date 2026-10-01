from django import forms
from django.utils.translation import gettext as _

from .models import Associate

# Certificates are uploaded and chased by staff from the admin area, never by
# anonymous visitors through the self-registration form.
PUBLIC_EXCLUDED_FIELDS = [
    'member',
    'membership_number',
    'renewal_date',
    'expiration_date',
    'active',
    'membership_type',
    'card_sent',
    'health_certificate_file',
    'health_certificate_expiry_date',
    'health_certificate_reminder_sent',
]


class AssociatePublicForm(forms.ModelForm):
    class Meta:
        model = Associate
        fields = '__all__'
        exclude = PUBLIC_EXCLUDED_FIELDS
        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'form-control','type': 'date', 'autoclose': True }),
        }


class AssociateForm(forms.ModelForm):
    class Meta:
        model = Associate
        fields = '__all__'
        exclude = ['member','membership_number', 'renewal_date','expiration_date','health_certificate_reminder_sent']
        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'form-control','type': 'date', 'autoclose': True }),
            'health_certificate_expiry_date': forms.DateInput(attrs={'class': 'form-control','type': 'date', 'autoclose': True }),
            'health_certificate_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure the date is formatted correctly for the HTML5 input field
        if self.instance and self.instance.birth_date:
            self.initial['birth_date'] = self.instance.birth_date.strftime('%Y-%m-%d')

    def clean_birth_date(self):
        """Parse the date correctly from user input."""
        birth_date = self.cleaned_data.get('birth_date')
        if isinstance(birth_date, str):
            try:
                return datetime.strptime(birth_date, '%Y-%m-%d').date()
            except ValueError:
                raise forms.ValidationError(_("Invalid date format."))
        return birth_date

class AssociateSearchForm(forms.Form):
    query = forms.CharField(
        label='Search',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Search by name, email, or parent email...')})
    )