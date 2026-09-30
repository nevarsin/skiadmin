from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DateField
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

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


def compute_diff(stock, checked_ids, existing_usages):
    """
    Works out what a Save does: which associates start consuming a skipass and
    which get theirs back (they were checked on a previous save but are not
    checked now, e.g. they turned up absent).

    A row is editable when it has stock left or was already consumed that day --
    someone who used their very last skipass today still has to be undoable.
    """
    editable_ids = {
        row.associate.pk for row in stock if row.remaining >= 1 or row.consumed_today
    }
    to_create = []
    to_delete = []
    consumed_ids = {usage.associate_id for usage in existing_usages}
    for row in stock:
        if row.associate.pk not in editable_ids:
            continue
        if row.associate.pk in checked_ids and row.associate.pk not in consumed_ids:
            to_create.append(row)
    for usage in existing_usages:
        if usage.associate_id in editable_ids and usage.associate_id not in checked_ids:
            to_delete.append(usage)
    return to_create, to_delete


def load_plan(selected_date):
    """The full editable picture for a ski day: what is left and what was consumed."""
    stock = skipass_stock()
    usages = list(
        SkipassUsage.objects
        .filter(date=selected_date)
        .select_related("associate", "article")
        .order_by("article__name", "associate__last_name", "associate__first_name")
    )
    consumed_today = {usage.associate_id for usage in usages}
    for row in stock:
        row.consumed_today = row.associate.pk in consumed_today
    return stock, usages


def plan_view(request):
    today = timezone.localdate()

    if request.method == "POST":
        selected_date = parse_ski_date(request.POST.get("date"), today)
        checked_ids = {
            int(key[len("include_"):])
            for key, value in request.POST.items()
            if key.startswith("include_") and value
        }
        confirmed = request.POST.get("confirm") == "1"
        stock, usages = load_plan(selected_date)
        to_create, to_delete = compute_diff(stock, checked_ids, usages)

        if to_delete and not confirmed:
            # Restoring a skipass is destructive: make the operator confirm it first.
            return render(request, "warehouse/confirm_changes.html", {
                "date": selected_date,
                "to_create": to_create,
                "to_delete": to_delete,
                "checked_ids": sorted(checked_ids),
            })

        with transaction.atomic():
            for row in to_create:
                SkipassUsage.objects.create(
                    date=selected_date,
                    associate=row.associate,
                    article=row.article,
                )
            deleted = 0
            for usage in to_delete:
                deleted += 1
                usage.delete()

        if deleted or to_create:
            parts = []
            if to_create:
                parts.append(ngettext(
                    "%(count)d skipass confirmed for %(date)s.",
                    "%(count)d skipass confirmed for %(date)s.",
                    len(to_create),
                ) % {"count": len(to_create), "date": selected_date.strftime("%d/%m/%Y")})
            if deleted:
                parts.append(ngettext(
                    "%(count)d skipass restored.",
                    "%(count)d skipass restored.",
                    deleted,
                ) % {"count": deleted})
            messages.success(request, " ".join(parts))
        else:
            messages.warning(request, _("Nothing to confirm."))
        return redirect(plan_url(selected_date))

    selected_date = parse_ski_date(request.GET.get("date"), today)
    stock, usages = load_plan(selected_date)
    has_consumed = bool(usages)
    editable = [row for row in stock if row.remaining >= 1 or row.consumed_today]
    # A day with nothing confirmed yet starts as "everyone shows up". Once it has
    # confirmations, only those are ticked, so a skipass given back stays given
    # back instead of silently reappearing on the next save.
    checked = [row for row in editable if row.consumed_today] if has_consumed else editable

    return render(request, "warehouse/plan.html", {
        "date": selected_date,
        "sections": group_by_article(stock),
        "consumed_count": len(usages),
        "has_consumed": has_consumed,
        "editable_count": len(editable),
        "checked_count": len(checked),
    })


def undo_view(request, day):
    selected_date = parse_ski_date(day, timezone.localdate())
    if request.method == "POST":
        deleted, _details = SkipassUsage.objects.filter(date=selected_date).delete()
        messages.success(request, ngettext(
            "%(count)d skipass records deleted for %(date)s.",
            "%(count)d skipass records deleted for %(date)s.",
            deleted,
        ) % {"count": deleted, "date": selected_date.strftime("%d/%m/%Y")})
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
