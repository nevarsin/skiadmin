import os
from datetime import datetime, time

from django.conf import settings
from django.db.models import F, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.associates.utils import (
    health_certificate_file_name,
    health_certificate_status,
    health_certificate_warn_days,
)
from apps.subscriptions.models import Subscription
from apps.transactions.models import Transaction
from apps.warehouse.models import SkipassUsage

from .forms import (
    AssociateReportForm,
    ReportTypeForm,
    SkipassReportForm,
    SubscriptionReportForm,
    TransactionReportForm,
)
from .utils import generate_pdf


def group_usages_by_article(usages):
    sections = {}
    for usage in usages:
        key = usage.article or _("Unknown article")
        sections.setdefault(key, []).append(usage)
    return sorted(sections.items(), key=lambda pair: str(pair[0]))


def select_report(request):
    if request.method == "POST":
        form = ReportTypeForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data["report_type"]
            if report_type == "associate":
                return render(request, "reports/report_form.html", {"form": AssociateReportForm(), "type": "associate"})
            elif report_type == "transaction":
                return render(request, "reports/report_form.html", {"form": TransactionReportForm(), "type": "transaction"})
            elif report_type == "subscription":
                return render(request, "reports/report_form.html", {"form": SubscriptionReportForm(), "type": "subscription"})
            elif report_type == "skipass":
                return render(request, "reports/report_form.html", {"form": SkipassReportForm(), "type": "skipass"})
    else:
        form = ReportTypeForm()
    return render(request, "reports/select_report.html", {"form": form})

REPORT_FORMS = {
    "associate": AssociateReportForm,
    "transaction": TransactionReportForm,
    "subscription": SubscriptionReportForm,
    "skipass": SkipassReportForm,
}

def generate_report(request, type):
    form_class = REPORT_FORMS.get(type)
    if form_class is None:
        return redirect("select_report")

    form = form_class(request.GET)
    if not form.is_valid():
        return render(request, "reports/report_form.html", {"form": form, "type": type})

    if type == "associate":
        qs = Associate.objects.all()
        if form.cleaned_data.get("active_only"):
            qs = qs.filter(active=True)
        pdf = generate_pdf("reports/associate_report.html", {"records": qs})
        return pdf

    elif type == "transaction":
        selected_date = datetime.strptime(form.cleaned_data["date"], "%Y-%m-%d").date()
        # build range covering the entire day
        start_dt = datetime.combine(selected_date, time.min).replace(tzinfo=timezone.get_current_timezone())
        end_dt = datetime.combine(selected_date, time.max).replace(tzinfo=timezone.get_current_timezone())
        qs = Transaction.objects.filter(date__gte=start_dt, date__lte=end_dt)

        # aggregate by article category
        category_totals = (
            qs.values(categories=F("lines__article__category"))
            .annotate(total=Sum("lines__price"))
            .order_by("categories")
        )

        # aggregate by payment method
        method_totals = (
            qs.values(methods=F("method"))
            .annotate(total=Sum("amount"))
            .order_by("methods")
        )

        # map choice labels
        method_labels = dict(Transaction.TRANSACTION_METHODS)
        category_labels = dict(Article.ARTICLE_CATEGORIES)

        # add readable labels
        for row in method_totals:
            row["method_display"] = method_labels.get(row["methods"], row["methods"])
        for row in category_totals:
            row["category_display"] = category_labels.get(row["categories"], row["categories"])

        # grand total
        grand_total = qs.aggregate(total=Sum("amount"))["total"] or 0

        # Filename translatable
        filename_prefix = _("report_transaction")

        pdf = generate_pdf(request, "reports/transaction_report.html", {
            "records": qs,
            "category_totals": category_totals,
            "method_totals": method_totals,
            "grand_total": grand_total,
            "date": start_dt,
            "static_root": settings.STATIC_ROOT,
        },  f"{filename_prefix}_{start_dt.strftime('%Y_%m_%d')}.pdf")
        return pdf

    elif type == "subscription":
        article = form.cleaned_data["article"]
        today = timezone.localdate()
        warn_days = health_certificate_warn_days()

        subscriptions = (
            Subscription.objects
            .filter(article=article)
            .exclude(associate_id=None)
            .select_related("associate")
            .order_by("associate__last_name", "associate__first_name", "associate_id")
        )

        rows = []
        counts = {"valid": 0, "expiring": 0, "expired": 0, "missing": 0}
        for subscription in subscriptions:
            associate = subscription.associate
            status, days_left = health_certificate_status(
                associate, today=today, warn_days=warn_days
            )
            counts[status] += 1
            rows.append({
                "associate": associate,
                "status": status,
                "days_left": days_left,
                # Just the filename: the full media path is noise on paper.
                "file_name": os.path.basename(health_certificate_file_name(associate)),
            })

        if form.cleaned_data.get("non_compliant_only"):
            rows = [row for row in rows if row["status"] != "valid"]

        filename_prefix = _("report_subscription_health_certificates")
        pdf = generate_pdf(request, "reports/subscription_report.html", {
            "article": article,
            "rows": rows,
            "counts": counts,
            "total": subscriptions.count(),
            "non_compliant": counts["expiring"] + counts["expired"] + counts["missing"],
            "warn_days": warn_days,
            "certification_required": article.certification_required,
            "date": today,
            "static_root": settings.STATIC_ROOT,
        }, f"{filename_prefix}_{today.strftime('%Y_%m_%d')}.pdf")
        return pdf

    elif type == "skipass":
        selected_date = datetime.strptime(form.cleaned_data["date"], "%Y-%m-%d").date()
        usages = (
            SkipassUsage.objects
            .filter(date=selected_date)
            .select_related("associate", "article")
            .order_by("article__name", "associate__last_name", "associate__first_name")
        )
        filename_prefix = _("report_skipass")

        pdf = generate_pdf(request, "reports/skipass_report.html", {
            "consumed_sections": group_usages_by_article(usages),
            "date": selected_date,
            "static_root": settings.STATIC_ROOT,
        }, f"{filename_prefix}_{selected_date.strftime('%Y_%m_%d')}.pdf")
        return pdf
