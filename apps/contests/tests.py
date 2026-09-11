import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from apps.associates.models import Associate

from .models import Contest, ContestParticipant
from .utils import format_time, parse_time, rank_participants


def create_associate(first, last, active=True):
    return Associate.objects.create(
        first_name=first,
        last_name=last,
        email=f"{first}.{last}@example.com",
        membership_type="standard",
        active=active,
        expiration_date=datetime.date(2026, 8, 31),
        address_street="Street",
        address_number="1",
        address_city="City",
        address_zip="12345",
        birth_date=datetime.date(1990, 1, 1),
        birth_city="Town",
        fiscal_code=f"{first.upper()}{last.upper()}1",
    )


def create_contest(**kwargs):
    data = {
        "name": "Test race",
        "date": datetime.date(2026, 1, 1),
        "location": "Tarcento",
    }
    data.update(kwargs)
    return Contest.objects.create(**data)


class ParseTimeTests(TestCase):
    def test_parse_and_format_roundtrip(self):
        for text in ("0:45.67", "125:45.67", "12:34.56"):
            parsed = parse_time(text)
            self.assertIsNotNone(parsed, text)
            self.assertEqual(format_time(parsed), text)

    def test_invalid_input(self):
        self.assertIsNone(parse_time(""))
        self.assertIsNone(parse_time(None))
        self.assertIsNone(parse_time("hello"))
        self.assertIsNone(parse_time("12:34"))

    def test_centiseconds(self):
        self.assertEqual(parse_time("1:00.05").microseconds, 50000)


class ContestModelTests(TestCase):
    def test_unique_participant_per_contest(self):
        contest = create_contest()
        associate = create_associate("Jane", "Doe")
        ContestParticipant.objects.create(contest=contest, associate=associate)
        with self.assertRaises(Exception):
            ContestParticipant.objects.create(contest=contest, associate=associate)


class ContestViewTests(TestCase):
    def test_add_contest_with_participants(self):
        jane = create_associate("Jane", "Doe")
        john = create_associate("John", "Doe")
        url = reverse("add_contest")
        response = self.client.post(
            url,
            {
                "name": "Sprint race",
                "date": "2026-02-15",
                "location": "Tarcento",
                "participants": [jane.pk, john.pk],
            },
        )
        self.assertRedirects(response, reverse("list_contests"))
        contest = Contest.objects.get(name="Sprint race")
        self.assertEqual(contest.status, Contest.STATUS_DRAFT)
        self.assertEqual(contest.participants.count(), 2)

    def test_edit_contest_updates_participants(self):
        contest = create_contest()
        jane = create_associate("Jane", "Doe")
        john = create_associate("John", "Doe")
        ContestParticipant.objects.create(contest=contest, associate=jane)
        response = self.client.post(
            reverse("edit_contest", args=[contest.pk]),
            {
                "name": contest.name,
                "date": "2026-01-01",
                "location": "Tarcento",
                "participants": [john.pk],
            },
        )
        self.assertRedirects(response, reverse("list_contests"))
        self.assertEqual(contest.participants.count(), 1)
        self.assertEqual(contest.participants.first().associate, john)

    def test_edit_contest_blocked_when_not_draft(self):
        contest = create_contest(status=Contest.STATUS_READY)
        response = self.client.get(reverse("edit_contest", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))

    def test_finalize_assigns_numbers_alphabetically(self):
        contest = create_contest()
        zebra = create_associate("Zoe", "Zulu")
        alpha = create_associate("Anna", "Alpha")
        ContestParticipant.objects.create(contest=contest, associate=zebra)
        ContestParticipant.objects.create(contest=contest, associate=alpha)
        response = self.client.post(reverse("finalize_contest", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))
        contest.refresh_from_db()
        self.assertEqual(contest.status, Contest.STATUS_READY)
        numbers = {
            p.associate.last_name: p.number
            for p in contest.participants.all()
        }
        self.assertEqual(numbers["Alpha"], 1)
        self.assertEqual(numbers["Zulu"], 2)

    def test_finalize_requires_participants(self):
        contest = create_contest()
        response = self.client.post(reverse("finalize_contest", args=[contest.pk]))
        self.assertRedirects(response, reverse("edit_contest", args=[contest.pk]))
        contest.refresh_from_db()
        self.assertEqual(contest.status, Contest.STATUS_DRAFT)

    def test_finalize_blocked_when_not_draft(self):
        contest = create_contest(status=Contest.STATUS_READY)
        response = self.client.post(reverse("finalize_contest", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))
        contest.refresh_from_db()
        self.assertEqual(contest.status, Contest.STATUS_READY)

    def test_finalize_get_renders_confirm_page(self):
        contest = create_contest()
        response = self.client.get(reverse("finalize_contest", args=[contest.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contests/confirm_action.html")
        contest.refresh_from_db()
        self.assertEqual(contest.status, Contest.STATUS_DRAFT)

    def test_finalize_confirm_blocked_when_not_draft(self):
        contest = create_contest(status=Contest.STATUS_READY)
        response = self.client.get(reverse("finalize_contest", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))

    def test_edit_times_saves_parsed_times(self):
        contest = create_contest(status=Contest.STATUS_READY)
        jane = create_associate("Jane", "Doe")
        participant = ContestParticipant.objects.create(
            contest=contest, associate=jane, number=1
        )
        data = {
            "participants-TOTAL_FORMS": "1",
            "participants-INITIAL_FORMS": "1",
            "participants-MIN_NUM_FORMS": "0",
            "participants-MAX_NUM_FORMS": "1000",
            "participants-0-id": participant.pk,
            "participants-0-race_time": "125:45.67",
        }
        response = self.client.post(
            reverse("edit_times", args=[contest.pk]), data
        )
        self.assertRedirects(response, reverse("list_contests"))
        participant.refresh_from_db()
        self.assertEqual(format_time(participant.race_time), "125:45.67")

    def test_edit_times_accepts_blank_for_dnf(self):
        contest = create_contest(status=Contest.STATUS_READY)
        jane = create_associate("Jane", "Doe")
        participant = ContestParticipant.objects.create(
            contest=contest, associate=jane, number=1
        )
        data = {
            "participants-TOTAL_FORMS": "1",
            "participants-INITIAL_FORMS": "1",
            "participants-MIN_NUM_FORMS": "0",
            "participants-MAX_NUM_FORMS": "1000",
            "participants-0-id": participant.pk,
            "participants-0-race_time": "",
        }
        self.client.post(reverse("edit_times", args=[contest.pk]), data)
        participant.refresh_from_db()
        self.assertIsNone(participant.race_time)

    def test_edit_times_blocked_after_ended(self):
        contest = create_contest(status=Contest.STATUS_ENDED)
        response = self.client.get(reverse("edit_times", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))

    def test_end_contest(self):
        contest = create_contest(status=Contest.STATUS_READY)
        response = self.client.post(reverse("end_contest", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))
        contest.refresh_from_db()
        self.assertEqual(contest.status, Contest.STATUS_ENDED)

    def test_end_contest_blocked_when_not_ready(self):
        contest = create_contest(status=Contest.STATUS_DRAFT)
        self.client.post(reverse("end_contest", args=[contest.pk]))
        contest.refresh_from_db()
        self.assertEqual(contest.status, Contest.STATUS_DRAFT)

    def test_end_get_renders_confirm_page(self):
        contest = create_contest(status=Contest.STATUS_READY)
        response = self.client.get(reverse("end_contest", args=[contest.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contests/confirm_action.html")
        contest.refresh_from_db()
        self.assertEqual(contest.status, Contest.STATUS_READY)

    def test_end_confirm_blocked_when_not_ready(self):
        contest = create_contest(status=Contest.STATUS_ENDED)
        response = self.client.get(reverse("end_contest", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))

    def test_delete_contest(self):
        contest = create_contest()
        response = self.client.post(reverse("delete_contest", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))
        self.assertFalse(Contest.objects.filter(pk=contest.pk).exists())

    def test_start_list_pdf_blocked_on_draft(self):
        contest = create_contest()
        response = self.client.get(reverse("start_list_pdf", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))

    def test_start_list_pdf_allowed_on_ready(self):
        contest = create_contest(status=Contest.STATUS_READY)
        response = self.client.get(reverse("start_list_pdf", args=[contest.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_results_pdf_blocked_before_ended(self):
        contest = create_contest(status=Contest.STATUS_READY)
        response = self.client.get(reverse("results_pdf", args=[contest.pk]))
        self.assertRedirects(response, reverse("list_contests"))

    def test_results_pdf_allowed_after_ended(self):
        contest = create_contest(status=Contest.STATUS_ENDED)
        response = self.client.get(reverse("results_pdf", args=[contest.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")


class RankingTests(TestCase):
    def test_ranking_order_ties_and_dnf(self):
        contest = create_contest(status=Contest.STATUS_ENDED)
        a = ContestParticipant.objects.create(
            contest=contest, associate=create_associate("Alice", "Able"), number=1
        )
        b = ContestParticipant.objects.create(
            contest=contest, associate=create_associate("Bob", "Bravo"), number=2
        )
        c = ContestParticipant.objects.create(
            contest=contest, associate=create_associate("Carol", "Charlie"), number=3
        )
        d = ContestParticipant.objects.create(
            contest=contest, associate=create_associate("Dan", "Delta"), number=4
        )

        a.race_time = parse_time("10:00.00")
        a.save(update_fields=["race_time"])
        b.race_time = parse_time("10:00.00")
        b.save(update_fields=["race_time"])
        c.race_time = parse_time("12:00.00")
        c.save(update_fields=["race_time"])
        d.race_time = None
        d.save(update_fields=["race_time"])

        with translation.override("en"):
            rows = rank_participants(
                contest.participants.order_by("race_time", "number")
            )
        positions = [row["position"] for row in rows]
        self.assertEqual(positions, [1, 1, 3, "DNF"])
        self.assertIsNone(rows[-1]["participant"].race_time)