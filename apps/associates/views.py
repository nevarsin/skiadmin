from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from .forms import AssociateForm, AssociatePublicForm, AssociateSearchForm
from .models import Associate
from .serializers import AssociateSerializer


def list_associates(request):
    associates = Associate.objects.all()
    query = request.GET.get('query')

    if query:
        # Use Q objects to perform a case-insensitive search across multiple fields
        associates = associates.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(parent_email__icontains=query)
        )
    form = AssociateSearchForm(request.GET or None)
    return render(request, "associates/list.html", {"associates": associates, 'form':form})

def add_associates(request):
    if request.method == "POST":
        form = AssociateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Associate created successfully."))
            return redirect("list_associates")
    else:
        form = AssociateForm()
    template_data = {}
    template_data["header"] = _("New Associate")
    return render(request, "associates/manage.html", {"form": form,'template_data': template_data})

def register_associate(request):
    if request.method == "POST":
        form = AssociatePublicForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Associate created successfully."))
            return render(request, "associates/register_thankyou.html")
    else:
        form = AssociatePublicForm()
    template_data = {}
    template_data["header"] = _("Register")
    return render(request, "associates/register.html", {"form": form,'template_data': template_data})

def delete_associates(request, pk):
    associate = get_object_or_404(Associate, pk=pk)
    if request.method == "POST":
        associate.delete()
        messages.success(request, _("Associate deleted successfully."))
        return redirect("list_associates")  # Replace with your associates listing view name
    return render(request, "associates/confirm_delete.html", {"object": associate, "type": "Associate"})

def edit_associates(request, pk):
    associate = get_object_or_404(Associate, pk=pk)

    if request.method == 'POST':
        form = AssociateForm(request.POST, instance=associate)
        if form.is_valid():
            form.save()
            messages.success(request, _("Associate")+" "+associate.first_name+" "+associate.last_name+" "+_("edited successfully."))
            return redirect('list_associates')  # Redirect to the list view after saving
    else:
        form = AssociateForm(instance=associate)
    template_data = {}
    template_data["header"] = _("Edit Associate")
    return render(request, 'associates/manage.html', {'form': form, 'associate': associate, 'template_data': template_data})