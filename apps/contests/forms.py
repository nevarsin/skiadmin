from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms

from apps.associates.models import Associate

from .models import Contest, ContestParticipant
from .utils import format_time, parse_time


class AssociateWidget(s2forms.ModelSelect2MultipleWidget):
    model = Associate
    search_fields = ["first_name__icontains", "last_name__icontains"]
    queryset = Associate.objects.filter(active=True)
    attr = {"data-minimum-input-length": 0}


class ContestForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        label=_("Participants"),
        queryset=Associate.objects.filter(active=True),
        widget=AssociateWidget,
        required=False,
    )

    class Meta:
        model = Contest
        fields = ["name", "date", "location"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }


class RaceTimeForm(forms.ModelForm):
    race_time = forms.CharField(
        label=_("Race time"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "M:SS.cc"}),
    )

    class Meta:
        model = ContestParticipant
        fields = ["race_time"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (
            self.instance
            and self.instance.pk
            and self.instance.race_time is not None
        ):
            self.initial["race_time"] = format_time(self.instance.race_time)

    def clean_race_time(self):
        value = self.cleaned_data.get("race_time")
        if not value:
            return None
        parsed = parse_time(value)
        if parsed is None:
            raise forms.ValidationError(
                _('Please use the format "M:SS.cc", e.g. "125:45.67".')
            )
        return parsed


RaceTimeFormSet = inlineformset_factory(
    Contest,
    ContestParticipant,
    form=RaceTimeForm,
    extra=0,
    can_delete=False,
)