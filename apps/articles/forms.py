from django import forms
from django.utils.translation import gettext as _

from .models import Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'

    def clean(self):
        """At most one article may hold each "current membership fee" flag.

        The transactions signal picks the flagged article with `.first()`, so two
        flagged rows would silently resolve to whichever has the lower id -- in
        practice last season's. Reject the clash here, where it is being edited.
        """
        cleaned = super().clean()
        for field in ("is_current_membership_fee", "is_current_minor_membership_fee"):
            if not cleaned.get(field):
                continue
            clash = Article.objects.filter(**{field: True})
            if self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            clash = clash.first()
            if clash is not None:
                self.add_error(
                    field,
                    _("Another article is already the current one: %(article)s. "
                      "Clear this flag there first.") % {"article": clash.name},
                )
        return cleaned
