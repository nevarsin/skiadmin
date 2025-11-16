import json
from io import BytesIO

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from weasyprint import HTML

from .forms import TransactionForm, TransactionLineFormSet
from .models import Associate, Transaction, TransactionLine
from .serializers import TransactionSerializer
from .utils import send_receipt_via_email


def list_transactions(request):
    transactions = Transaction.objects.select_related("associate").all().order_by("-id")
    return render(request, "transactions/list.html", {"transactions": transactions})

def transaction_detail(request, pk):
    transaction = Transaction.objects.get(pk=pk)
    transaction_lines = TransactionLine.objects.filter(transaction_id=transaction.id)
    return render(request, "transactions/detail.html", {"transaction": transaction, "transaction_lines": transaction_lines})

def add_transactions(request):
    if request.method == "POST":
        form = TransactionForm(request.POST)
        formset = TransactionLineFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            transaction = form.save(commit=False)
            transaction.save()
            lines = formset.save(commit=False)

            for line in lines:
                line.transaction = transaction
                line.save()

            transaction.update_total()  # Ensure total is updated
            messages.success(request, _("Transaction saved successfully."))
            return redirect("list_transactions")
    else:
        form = TransactionForm()
        formset = TransactionLineFormSet()
    template_data = {}
    template_data["header"] = _("New Transaction")
    return render(request, "transactions/manage.html", {"form": form,"formset": formset, "template_data": template_data })

def edit_transactions(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        formset = TransactionLineFormSet(request.POST, instance=transaction)
        print(formset.errors)
        if form.is_valid() and formset.is_valid():

            transaction = form.save()
            transaction.save()
            lines = formset.save()

            for line in lines:
                line.transaction = transaction
                line.save()

            transaction.update_total()  # Ensure total is updated
            messages.success(request, _("Transaction saved successfully."))
            return redirect("list_transactions")

    else:
        form = TransactionForm(instance=transaction)
        formset = TransactionLineFormSet(instance=transaction)
    template_data = {}
    template_data["header"] = _("Edit Transaction")
    return render(request, 'transactions/manage.html', {'form': form, 'formset':formset, 'transaction': transaction, 'template_data': template_data})

def delete_transactions(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == "POST":
        transaction.delete()
        messages.success(request, _("Transaction deleted successfully."))
        return redirect("list_transactions")  # Replace with your transactions listing view name
    return render(request, "transactions/confirm_delete.html", {"object": transaction, "type": "Transaction"})

def generate_receipt(request, pk):
    # Gather data for the report
    transaction = get_object_or_404(Transaction, pk=pk)
    transaction_lines = TransactionLine.objects.filter(transaction_id=transaction.id)

    # Render the HTML template into a string
    html_string = render_to_string("transactions/receipt.html", {"transaction": transaction, "transaction_lines":transaction_lines })

    # Generate a PDF using WeasyPrint
    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(pdf_file)
    pdf_file.seek(0)

    # Send the PDF as a response
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=receipt.pdf"
    response["X-Frame-Options"] = "SAMEORIGIN"
    response["Content-Security-Policy"] = "frame-ancestors 'self'"
    return response

def send_receipt(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    transaction_lines = TransactionLine.objects.filter(transaction=transaction)

    try:
        data = json.loads(request.body.decode("utf-8"))
        to_email = data.get("email", transaction.associate.email)
    except Exception:
        to_email = transaction.associate.email

    send_receipt_via_email(transaction, transaction_lines, to_email)
    return JsonResponse({"status": "ok"})