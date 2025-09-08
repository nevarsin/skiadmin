from django import forms
from .models import Article
from django.utils.translation import gettext as _

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'
        

        