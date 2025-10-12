from django.shortcuts import render
from .forms import ReportTypeForm, AssociateReportForm, TransactionReportForm
from apps.associates.models import Associate
from apps.transactions.models import Transaction
from .utils import generate_pdf
from django.utils import timezone
from datetime import datetime, time


def select_report(request):
    if request.method == "POST":
        form = ReportTypeForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data["report_type"]
            if report_type == "associate":
                return render(request, "reports/report_form.html", {"form": AssociateReportForm(), "type": "associate"})
            elif report_type == "transaction":
                return render(request, "reports/report_form.html", {"form": TransactionReportForm(), "type": "transaction"})
    else:
        form = ReportTypeForm()
    return render(request, "reports/select_report.html", {"form": form})

def generate_report(request, type):
    if type == "associate":
        form = AssociateReportForm(request.GET)
        if form.is_valid():
            qs = Associate.objects.all()
            if form.cleaned_data.get("active_only"):
                qs = qs.filter(active=True)
            pdf = generate_pdf("reports/associate_report.html", {"records": qs})
            return pdf
    elif type == "transaction":
        form = TransactionReportForm(request.GET)
        if form.is_valid():
            selected_date = datetime.strptime(form.cleaned_data["date"], "%Y-%m-%d").date()
            # build range covering the entire day
            start_dt = datetime.combine(selected_date, time.min).replace(tzinfo=timezone.get_current_timezone())
            end_dt = datetime.combine(selected_date, time.max).replace(tzinfo=timezone.get_current_timezone())
            qs = Transaction.objects.filter(date__gte=start_dt, date__lte=end_dt)
            pdf = generate_pdf("reports/transaction_report.html", {"records": qs})
            return pdf