from django import forms
from .models import Associate

class AssociateForm(forms.ModelForm):
    class Meta:
        model = Associate
        fields = '__all__'
        exclude = ['member','membership_number', 'renewal_date']
        widgets = {
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',  # Use HTML5 date input
            }),
        }