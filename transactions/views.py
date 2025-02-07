from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.template.loader import render_to_string
from .serializers import TransactionSerializer
from weasyprint import HTML
from io import BytesIO
from .models import Transaction, TransactionLine, Associate
from .forms import TransactionForm,TransactionLineFormSet

def transactions_list(request):
    transactions = Transaction.objects.select_related("associate").all()  
    return render(request, "transactions/list.html", {"transactions": transactions})


def transaction_detail(request, pk):
    transaction = Transaction.objects.get(pk=pk)
    transaction_lines = TransactionLine.objects.filter(transaction_id=transaction.id)
    return render(request, "transactions/detail.html", {"transaction": transaction, "transaction_lines": transaction_lines})

def add_transaction(request):
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
            messages.success(request, "Transaction saved successfully.")
            return redirect("transactions_list")
    else:
        form = TransactionForm()
        formset = TransactionLineFormSet()
        return render(request, "transactions/add.html", {
            "form": form,
            "formset": formset
        })

def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        formset = TransactionLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            transaction = form.save(commit=False)
            transaction.save()
            lines = formset.save(commit=False)

            for line in lines:
                line.transaction = transaction
                line.save()

            transaction.update_total()  # Ensure total is updated
            messages.success(request, "Transaction saved successfully.")
    else:
        form = TransactionForm(request.POST, instance=transaction)
        formset = TransactionLineFormSet(request.POST)
    template_data = {}
    template_data["header"] = "Edit Transaction" 
    return render(request, 'transactions/add.html', {'form': form, 'transaction': transaction, 'template_data': template_data})

def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == "POST":
        transaction.delete()
        messages.success(request, "Transaction deleted successfully.")
        return redirect("transactions_list")  # Replace with your transactions listing view name
    return render(request, "transactions/confirm_delete.html", {"object": transaction, "type": "Transaction"})

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




