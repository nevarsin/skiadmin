from weasyprint import HTML
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static
from .serializers import TransactionSerializer
from .models import Transaction, TransactionLine, Associate
from .forms import TransactionForm,TransactionLineFormSet

def list_transactions(request):
    transactions = Transaction.objects.select_related("associate").all()
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
    html_string = render_to_string("transactions/report.html", {"transaction": transaction, "transaction_lines":transaction_lines })

    # Generate a PDF using WeasyPrint
    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(pdf_file)
    pdf_file.seek(0)

    # Send the PDF as a response
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=report.pdf"
    return response




