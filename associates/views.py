from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .serializers import AssociateSerializer
from .models import Associate
from .forms import AssociateForm

@api_view(['GET'])
def associate_list(request):
    associates = Associate.objects.all()
    return render(request, "associates/list.html", {"associates": associates})

@api_view(['GET'])
def associate_detail(request, pk):
    associate = Associate.objects.get(pk=pk)
    return render(request, "associates/detail.html", {"associate": associate})

@swagger_auto_schema(
    method='post',
    request_body=AssociateSerializer,
    responses={201: "Associate created successfully.", 400: "Invalid input data."},
)
@api_view(['POST'])
def add_associate(request):
    if request.method == "POST":
        form = AssociateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("associate_list")  # Adjust to the correct URL name
    else:
        form = AssociateForm()
    return render(request, "associates/add.html", {"form": form})

@swagger_auto_schema(
    method='post',    
    responses={201: "Associate deleted successfully.", 400: "Invalid input data."},
)
@api_view(['POST'])
def delete_associate(request, pk):
    associate = get_object_or_404(Associate, pk=pk)
    if request.method == "POST":
        associate.delete()
        messages.success(request, "Associate deleted successfully.")
        return redirect("associate_list")  # Replace with your associates listing view name
    return render(request, "associates/confirm_delete.html", {"object": associate, "type": "Associate"})