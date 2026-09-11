from django.contrib import messages
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from .forms import ContestForm, RaceTimeFormSet
from .models import Contest, ContestParticipant
from .utils import rank_participants, render_pdf


def list_contests(request):
    contests = Contest.objects.prefetch_related("participants").all()
    return render(request, "contests/list.html", {"contests": contests})


def add_contest(request):
    if request.method == "POST":
        form = ContestForm(request.POST)
        if form.is_valid():
            contest = form.save()
            ContestParticipant.objects.bulk_create(
                [
                    ContestParticipant(contest=contest, associate=associate)
                    for associate in form.cleaned_data["participants"]
                ]
            )
            messages.success(request, _("Contest created successfully."))
            return redirect("list_contests")
    else:
        form = ContestForm()
    template_data = {}
    template_data["header"] = _("New Contest")
    return render(
        request,
        "contests/manage.html",
        {"form": form, "template_data": template_data},
    )


def edit_contest(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    if contest.status != Contest.STATUS_DRAFT:
        messages.error(request, _("Only draft contests can be edited."))
        return redirect("list_contests")

    if request.method == "POST":
        form = ContestForm(request.POST, instance=contest)
        if form.is_valid():
            contest = form.save()
            selected = form.cleaned_data["participants"]
            contest.participants.exclude(associate__in=selected).delete()
            for associate in selected:
                ContestParticipant.objects.get_or_create(
                    contest=contest, associate=associate
                )
            messages.success(request, _("Contest updated successfully."))
            return redirect("list_contests")
    else:
        form = ContestForm(
            instance=contest,
            initial={
                "participants": contest.participants.values_list(
                    "associate__id", flat=True
                )
            },
        )
    template_data = {}
    template_data["header"] = _("Edit Contest")
    return render(
        request,
        "contests/manage.html",
        {"form": form, "contest": contest, "template_data": template_data},
    )


def finalize_contest(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    if contest.status != Contest.STATUS_DRAFT:
        messages.error(request, _("Only draft contests can be finalized."))
        return redirect("list_contests")

    if request.method == "POST":
        participants = list(
            contest.participants.select_related("associate").order_by(
                "associate__last_name", "associate__first_name"
            )
        )
        if not participants:
            messages.error(request, _("Add at least one participant before finalizing."))
            return redirect("edit_contest", pk=contest.pk)

        for number, participant in enumerate(participants, start=1):
            participant.number = number
        ContestParticipant.objects.bulk_update(participants, ["number"])
        contest.status = Contest.STATUS_READY
        contest.save(update_fields=["status"])
        messages.success(request, _("Contest finalized, numbers assigned."))
        return redirect("list_contests")

    return render(
        request,
        "contests/confirm_action.html",
        {
            "object": contest,
            "headline": _("Finalize contest?"),
            "description": _(
                "Assign start numbers to participants and move the contest to Ready."
            ),
            "action_label": _("Finalize"),
        },
    )


def edit_times(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    if contest.status != Contest.STATUS_READY:
        messages.error(request, _("Race times can only be entered before the contest ends."))
        return redirect("list_contests")

    if request.method == "POST":
        formset = RaceTimeFormSet(request.POST, instance=contest)
        if formset.is_valid():
            formset.save()
            messages.success(request, _("Race times saved successfully."))
            return redirect("list_contests")
    else:
        formset = RaceTimeFormSet(instance=contest)
    return render(
        request,
        "contests/edit_times.html",
        {"contest": contest, "formset": formset},
    )


def end_contest(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    if contest.status != Contest.STATUS_READY:
        messages.error(request, _("Only ready contests can be ended."))
        return redirect("list_contests")

    if request.method == "POST":
        contest.status = Contest.STATUS_ENDED
        contest.save(update_fields=["status"])
        messages.success(request, _("Contest ended."))
        return redirect("list_contests")

    return render(
        request,
        "contests/confirm_action.html",
        {
            "object": contest,
            "headline": _("End contest?"),
            "description": _(
                "Marking the contest as ended will lock race times and unlock the results report."
            ),
            "action_label": _("End contest"),
        },
    )


def delete_contest(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    if request.method == "POST":
        contest.delete()
        messages.success(request, _("Contest deleted successfully."))
        return redirect("list_contests")
    return render(
        request,
        "contests/confirm_delete.html",
        {"object": contest, "type": _("Contest")},
    )


def start_list_pdf(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    if contest.status == Contest.STATUS_DRAFT:
        messages.error(request, _("Finalize the contest before printing the start list."))
        return redirect("list_contests")

    participants = contest.participants.select_related("associate").order_by("number")
    filename = f"{contest.name.replace(' ', '_')}_{contest.date:%Y%m%d}_start_list.pdf"
    return render_pdf(
        request,
        "contests/start_list.html",
        {"contest": contest, "participants": participants},
        filename=filename,
    )


def results_pdf(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    if contest.status != Contest.STATUS_ENDED:
        messages.error(request, _("Results are available once the contest has ended."))
        return redirect("list_contests")

    participants = contest.participants.select_related("associate").order_by(
        F("race_time").asc(nulls_last=True), "number"
    )
    filename = f"{contest.name.replace(' ', '_')}_{contest.date:%Y%m%d}_results.pdf"
    return render_pdf(
        request,
        "contests/results.html",
        {"contest": contest, "results": rank_participants(participants)},
        filename=filename,
    )