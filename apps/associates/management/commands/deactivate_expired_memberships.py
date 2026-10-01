from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.associates.models import Associate


class Command(BaseCommand):
    help = "Deactivate memberships whose expiration_date is in the past."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )
        parser.add_argument(
            "--today",
            type=date.fromisoformat,
            default=None,
            help="Override today's date (YYYY-MM-DD), e.g. to backfill a past boundary.",
        )

    def handle(self, *args, **options):
        today = options["today"] or timezone.localdate()

        expired = Associate.objects.filter(active=True, expiration_date__lt=today)

        if options["dry_run"]:
            for associate in expired.only("first_name", "last_name", "expiration_date")[:50]:
                self.stdout.write(
                    f"  {associate.first_name} {associate.last_name} "
                    f"(expired {associate.expiration_date})"
                )
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: would deactivate {expired.count()} membership(s)."
                )
            )
            return

        updated = expired.update(active=False, card_sent=False)
        self.stdout.write(
            self.style.SUCCESS(f"Deactivated {updated} expired membership(s).")
        )
