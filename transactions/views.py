from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.template.loader import render_to_string
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .serializers import TransactionSerializer
from weasyprint import HTML
from io import BytesIO
from .models import Transaction
from .forms import TransactionForm

@api_view(['GET'])
def transaction_list(request):
    transactions = Transaction.objects.all()
    return render(request, "transactions/list.html", {"transactions": transactions})

@api_view(['GET'])
def transaction_detail(request, pk):
    transaction = Transaction.objects.get(pk=pk)
    return render(request, "transactions/detail.html", {"transaction": transaction})

@swagger_auto_schema(
    method='post',
    request_body=TransactionSerializer,
    responses={201: "Transaction created successfully.", 400: "Invalid input data."},
)
@api_view(['POST'])
def add_transaction(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("transaction_list")  # Adjust to the correct URL name
    else:
        form = TransactionForm()
    return render(request, "transactions/add.html", {"form": form})

@swagger_auto_schema(
    method='post',    
    responses={201: "Transaction deleted successfully.", 400: "Invalid input data."},
)
@api_view(['POST'])
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == "POST":
        transaction.delete()
        messages.success(request, "Transaction deleted successfully.")
        return redirect("transactions_list")  # Replace with your transactions listing view name
    return render(request, "transactions/confirm_delete.html", {"object": transaction, "type": "Transaction"})

@api_view(['GET'])
def generate_report(request):
    # Gather data for the report
    transactions = Transaction.objects.all()
    exporting_to_pdf = request.GET.get("export") == "pdf"

    # Check if the user wants a PDF export
    if exporting_to_pdf:        
        # Render the HTML template into a string
        html_string = render_to_string("transactions/report.html", {"transactions": transactions, "exporting_to_pdf": exporting_to_pdf})

        # Generate a PDF using WeasyPrint
        pdf_file = BytesIO()
        HTML(string=html_string).write_pdf(pdf_file)
        pdf_file.seek(0)

        # Send the PDF as a response
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = "inline; filename=report.pdf"
        return response

    # If not exporting, render the HTML page normally
    return render(request, "transactions/report.html", {"transactions": transactions, "exporting_to_pdf": exporting_to_pdf})