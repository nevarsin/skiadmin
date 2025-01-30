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
                'autoclose': True
            }),
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
                raise forms.ValidationError("Invalid date format.")
        return birth_date

class AssociateSearchForm(forms.Form):
    query = forms.CharField(
        label='Search',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search by name, email, or parent email...'})
    )