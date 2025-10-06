from django import forms
from django.utils.translation import gettext as _

from .models import Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'
        

        