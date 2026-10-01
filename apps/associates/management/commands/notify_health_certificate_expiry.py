from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.associates.models import Associate
from apps.associates.utils import (
    health_certificate_recipients,
    health_certificate_warn_days,
    send_health_certificate_expiry_email,
)
from apps.subscriptions.models import Subscription


class Command(BaseCommand):
    help = (
        "Chase health certificates: email associates whose certificate is about "
        "to expire, email those whose certificate has expired, and clear the "
        "expired one."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would happen without sending or writing anything.",
        )
        parser.add_argument(
            "--today",
            type=date.fromisoformat,
            default=None,
            help="Override today's date (YYYY-MM-DD), e.g. to test a past boundary.",
        )

    def handle(self, *args, **options):
        today = options["today"] or timezone.localdate()
        warn_days = health_certificate_warn_days()

        expiring = self._expiring(today, warn_days)
        expired = self._expired(today)

        self.stdout.write(
            f"Certificates expiring within {warn_days} day(s) or already expired: {today}"
        )

        reminded = self._notify(expiring, today, expired=False, dry_run=options["dry_run"])
        cleared = self._notify(expired, today, expired=True, dry_run=options["dry_run"])

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: would send {reminded} expiry reminder(s) and "
                    f"{cleared} expired notification(s)."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {reminded} expiry reminder(s) and {cleared} expired notification(s)."
            )
        )

    def _subscribed_ids(self):
        """Associates signed up for an activity that demands a certificate.

        The certificate lives on the Associate and is valid all season, but we
        only chase the members who are actually enrolled in such an activity --
        there is no point emailing someone who never plays.
        """
        return Subscription.objects.filter(
            article__certification_required=True, associate__isnull=False
        ).values_list("associate_id", flat=True)

    def _base_queryset(self):
        # FileField stores '' rather than NULL for a cleared file, so both need
        # excluding to be safe whichever the column happens to hold.
        return Associate.objects.filter(
            pk__in=self._subscribed_ids()
        ).exclude(
            Q(health_certificate_file="") | Q(health_certificate_file__isnull=True)
        )

    def _expiring(self, today, warn_days):
        return self._base_queryset().filter(
            health_certificate_expiry_date__isnull=False,
            health_certificate_expiry_date__gt=today,
            health_certificate_expiry_date__lte=today + timedelta(days=warn_days),
            health_certificate_reminder_sent=False,
        ).order_by("health_certificate_expiry_date", "id")

    def _expired(self, today):
        # Strict: a certificate whose expiry date is today is still valid.
        return self._base_queryset().filter(
            health_certificate_expiry_date__isnull=False,
            health_certificate_expiry_date__lt=today,
        ).order_by("health_certificate_expiry_date", "id")

    def _notify(self, queryset, today, expired, dry_run):
        sent = 0
        for associate in queryset:
            label = (
                f"expired {associate.health_certificate_expiry_date}"
                if expired
                else f"expires {associate.health_certificate_expiry_date}"
            )
            self.stdout.write(f"  {associate.first_name} {associate.last_name} ({label})")

            if not health_certificate_recipients(associate):
                self.stdout.write(
                    self.style.WARNING(
                        f"    skipped: no email or parent email on file for {associate.pk}"
                    )
                )
                continue

            if dry_run:
                sent += 1
                continue

            try:
                send_health_certificate_expiry_email(
                    associate, (associate.health_certificate_expiry_date - today).days
                )
            except Exception as exc:
                # One unreachable mailbox must not stop the rest of the run.
                self.stderr.write(
                    self.style.ERROR(
                        f"    failed to email {associate.pk}: {exc}"
                    )
                )
                continue

            if expired:
                # An expired certificate is no longer evidence of anything, and
                # the compliance report needs it to show up as MISSING so the
                # member gets chased for a fresh one.
                associate.health_certificate_file = ""
                associate.health_certificate_expiry_date = None
                associate.health_certificate_reminder_sent = False
                associate.save(
                    update_fields=[
                        "health_certificate_file",
                        "health_certificate_expiry_date",
                        "health_certificate_reminder_sent",
                    ]
                )
            else:
                # The flag is what stops the next cron run mailing them again.
                associate.health_certificate_reminder_sent = True
                associate.save(update_fields=["health_certificate_reminder_sent"])
            sent += 1
        return sent