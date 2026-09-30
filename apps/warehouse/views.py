from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DateField
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import SkipassUsage, skipass_stock


def parse_ski_date(raw, default):
    """Parses a YYYY-MM-DD string, falling back to `default` on anything unparseable."""
    try:
        return DateField().to_python(raw) or default
    except (ValidationError, TypeError):
        return default


def plan_url(day):
    return f"{reverse('warehouse_plan')}?date={day.isoformat()}"


def group_by_article(items):
    sections = {}
    for item in items:
        key = item.article or _("Unknown article")
        sections.setdefault(key, []).append(item)
    return sorted(sections.items(), key=lambda pair: str(pair[0]))


def plan_view(request):
    today = timezone.localdate()

    if request.method == "POST":
        selected_date = parse_ski_date(request.POST.get("date"), today)
        checked_ids = {
            int(key[len("include_"):])
            for key, value in request.POST.items()
            if key.startswith("include_") and value
        }
        created = 0
        with transaction.atomic():
            stock = {row.associate.pk: row for row in skipass_stock() if row.remaining >= 1}
            for associate_id in checked_ids:
                row = stock.get(associate_id)
                if row is None:
                    continue
                _usage, was_created = SkipassUsage.objects.get_or_create(
                    date=selected_date,
                    associate_id=associate_id,
                    defaults={"article": row.article},
                )
                if was_created:
                    created += 1
        if created:
            messages.success(request, _("%(count)d skipass confirmed for %(date)s.") % {
                "count": created,
                "date": selected_date.strftime("%d/%m/%Y"),
            })
        else:
            messages.warning(request, _("Nothing to confirm."))
        return redirect(plan_url(selected_date))

    selected_date = parse_ski_date(request.GET.get("date"), today)
    stock = skipass_stock()
    usages = list(
        SkipassUsage.objects
        .filter(date=selected_date)
        .select_related("associate", "article")
        .order_by("article__name", "associate__last_name", "associate__first_name")
    )

    return render(request, "warehouse/plan.html", {
        "date": selected_date,
        "sections": group_by_article(stock),
        "consumed_sections": group_by_article(usages),
        "pending_count": sum(1 for row in stock if row.remaining >= 1),
    })


def undo_view(request, day):
    selected_date = parse_ski_date(day, timezone.localdate())
    if request.method == "POST":
        deleted, _details = SkipassUsage.objects.filter(date=selected_date).delete()
        messages.success(request, _("%(count)d skipass records deleted for %(date)s.") % {
            "count": deleted,
            "date": selected_date.strftime("%d/%m/%Y"),
        })
        return redirect(plan_url(selected_date))

    usages = (
        SkipassUsage.objects
        .filter(date=selected_date)
        .select_related("associate", "article")
        .order_by("article__name", "associate__last_name")
    )
    return render(request, "warehouse/confirm_delete.html", {
        "date": selected_date,
        "usages": usages,
    })
