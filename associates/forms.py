from django import forms
from .models import Associate

class AssociateForm(forms.ModelForm):
    class Meta:
        model = Associate
        fields = ['first_name', 'last_name', 'email']