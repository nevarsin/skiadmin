from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.associates.models import Associate


class Contest(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_READY = "ready"
    STATUS_ENDED = "ended"

    STATUSES = [
        (STATUS_DRAFT, _("Draft")),
        (STATUS_READY, _("Ready")),
        (STATUS_ENDED, _("Ended")),
    ]

    name = models.CharField(_("Name"), max_length=200)
    date = models.DateField(_("Date"))
    location = models.CharField(_("Location"), max_length=200)
    status = models.CharField(
        _("Status"),
        max_length=10,
        choices=STATUSES,
        default=STATUS_DRAFT,
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.name} - {self.date.strftime('%d/%m/%Y')}"


class ContestParticipant(models.Model):
    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE, related_name="participants"
    )
    associate = models.ForeignKey(
        Associate, on_delete=models.CASCADE, related_name="contest_participations"
    )
    number = models.PositiveIntegerField(_("Number"), null=True, blank=True)
    race_time = models.DurationField(_("Race time"), null=True, blank=True)

    class Meta:
        ordering = ["number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["contest", "associate"],
                name="unique_participant_per_contest",
            ),
            models.UniqueConstraint(
                fields=["contest", "number"],
                name="unique_number_per_contest",
            ),
        ]

    def __str__(self):
        name = f"{self.associate.first_name} {self.associate.last_name}"
        if self.number is not None:
            return f"#{self.number} {name}"
        return name