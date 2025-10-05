from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Settings
from .forms import SettingsForm

def manage_settings(request):
    options = Settings.objects.all()

    if request.method == "POST":
        form = SettingsForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Option added successfully."))
            return redirect("manage_settings")
    else:
        form = SettingsForm()

    return render(request, "core/settings.html", {"options": options, "form": form})

def edit_settings(request, option_id):
    option = get_object_or_404(Settings, id=option_id)

    if request.method == "POST":
        option.value = request.POST.get("value", option.value)
        option.save()
        messages.success(request, _("Option updated successfully."))

    return redirect("manage_settings")

def delete_settings(request, option_id):
    option = get_object_or_404(Settings, id=option_id)
    option.delete()
    messages.success(request, _("Option deleted successfully."))
    return redirect("manage_settings")
