from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext as _
from .models import Subscription
from .forms import SubscriptionForm

def list_subscriptions(request):
    subscriptions = Subscription.objects.all()
    return render(request, "subscriptions/list.html", {"subscriptions": subscriptions})

def add_subscription(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Subscription created successfully."))
            return redirect("list_subscriptions")
    else:
        form = SubscriptionForm()
    template_data = {}
    template_data["header"] = _("New Subscription")
    return render(request, "subscriptions/manage.html", {"form": form,'template_data': template_data})

def delete_subscription(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    if request.method == "POST":
        subscription.delete()
        messages.success(request, _("Subscription deleted successfully."))
        return redirect("list_subscriptions")  # Replace with your associates listing view name
    return render(request, "subscriptions/confirm_delete.html", {"object": subscription, "type": "Subscription"})

def edit_subscription(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)

    if request.method == 'POST':
        form = SubscriptionForm(request.POST, request.FILES, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, _("Subscription")+" "+_("edited successfully."))
            return redirect('list_subscriptions')  # Redirect to the list view after saving
    else:
        form = SubscriptionForm(instance=subscription)
    template_data = {}
    template_data["header"] = _("Edit Subscription")
    return render(request, 'subscriptions/manage.html', {'form': form, 'subscription': subscription, 'template_data': template_data})

