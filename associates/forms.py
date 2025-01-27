from django import forms
from .models import Associate

class AssociateForm(forms.ModelForm):
    class Meta:
        model = Associate
        fields = '__all__'
        exclude = ['member','membership_number', 'renewal_date','expiration_date']
        widgets = {
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',  # Use HTML5 date input
            }),
        }

class AssociateSearchForm(forms.Form):
    query = forms.CharField(
        label='Search',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search by name, email, or parent email...'})
    )