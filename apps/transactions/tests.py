from datetime import date
from unittest import mock

from django.test import Client, TestCase

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.transactions.models import Transaction, TransactionLine
from apps.transactions.forms import TransactionLineFormSet


def _make_associate(first_name="Test", membership_type="standard", active=True,
                    birth_date=date(1990, 1, 1), email="test@example.com", **kw):
    return Associate.objects.create(
        first_name=first_name, last_name="User", email=email,
        membership_type=membership_type, active=active,
        birth_date=birth_date, birth_city="Trento", birth_country="IT",
        expiration_date=date(2026, 8, 31),
        address_street="Via Roma", address_number="1", address_city="Tarcento",
        address_zip="33018", address_country="IT", **kw,
    )


def _make_article(name="Presciistica", price=80, category="skipass"):
    return Article.objects.create(name=name, price=price, category=category)


def _formset_data(assoc_id, article_id, *, total_forms=10, filled_forms=0, qty=1, price=80):
    # Browser-realistic: manage.html's JS pre-fills "0.00" in line_total of empty rows.
    data = {
        "associate": str(assoc_id), "method": "cash", "amount": str(price),
        "lines-TOTAL_FORMS": str(total_forms),
        "lines-INITIAL_FORMS": str(filled_forms),
        "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
    }
    for i in range(total_forms):
        prefix = f"lines-{i}-"
        data[f"{prefix}associate"] = str(assoc_id) if i == 0 else ""
        data[f"{prefix}article"] = str(article_id) if i == 0 else ""
        data[f"{prefix}quantity"] = str(qty) if i == 0 else ""
        data[f"{prefix}price"] = str(price) if i == 0 else ""
        data[f"{prefix}line_total"] = str(price) if i == 0 else "0.00"
    return data


def _tessera_articles():
    _make_article("Tessera 2025/2026", price=15, category="membership")
    _make_article("Tessera ragazzi 2025/2026", price=10, category="membership")


# ---------- formset blank-row validation ----------

class TransactionFormsetTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.associate = _make_associate("Std")
        cls.article = _make_article()
        # Signal unconditionally looks these up by name
        _tessera_articles()

    def test_blank_extra_rows_do_not_fail_validation(self):
        """9 unfilled extra rows (browser submits all 10) should not cause errors."""
        data = _formset_data(self.associate.id, self.article.id)
        fs = TransactionLineFormSet(data)
        self.assertTrue(fs.is_valid(), fs.errors)

    def test_add_with_blank_extra_rows_saves_one_line(self):
        """POST from the browser (10 rows, only row 0 filled) should save one line."""
        data = _formset_data(self.associate.id, self.article.id)
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post("/transactions/add/", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        txn = Transaction.objects.order_by("-id").first()
        self.assertEqual(txn.lines.count(), 1)

    def _make_transaction_with_line(self):
        txn = Transaction.objects.create(associate=self.associate, method="cash", amount=80)
        TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.article,
            quantity=1, price=80, line_total=80,
        )
        return txn

    def test_edit_blank_extra_rows_saved_like_browser(self):
        """Browser-realistic edit POST: existing line + 10 rows w/ line_total='0.00' on empty rows."""
        txn = self._make_transaction_with_line()
        data = {
            "associate": str(self.associate.id), "method": "cash", "amount": "160.00",
            "lines-TOTAL_FORMS": "11", "lines-INITIAL_FORMS": "1",
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
        }
        line = txn.lines.first()
        for k, v in {"id": str(line.id), "associate": str(self.associate.id),
                     "article": str(self.article.id), "quantity": "2",
                     "price": "80.00", "line_total": "160.00"}.items():
            data[f"lines-0-{k}"] = v
        for i in range(1, 11):
            for k in ("associate", "article", "quantity", "price", "line_total"):
                data[f"lines-{i}-{k}"] = "" if k != "line_total" else "0.00"
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post(f"/transactions/{txn.id}/edit", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        txn.refresh_from_db()
        self.assertEqual(txn.lines.count(), 1)
        self.assertEqual(txn.lines.first().quantity, 2)

    def _blank_line_data(self, txn, kept_lines=()):
        """Browser-realistic POST that blanks existing lines but preserves hidden id/transaction."""
        lines = list(txn.lines.all().order_by("id"))
        data = {
            "associate": str(self.associate.id), "method": "cash", "amount": "0.00",
            "lines-TOTAL_FORMS": "10", "lines-INITIAL_FORMS": str(len(lines)),
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
        }
        # Blank all existing lines (hidden id/transaction preserved, like the Clear button)
        for i, line in enumerate(lines):
            data[f"lines-{i}-id"] = str(line.id)
            data[f"lines-{i}-transaction"] = str(txn.id)
            if line in kept_lines:
                data[f"lines-{i}-associate"] = str(self.associate.id)
                data[f"lines-{i}-article"] = str(line.article_id)
                data[f"lines-{i}-quantity"] = str(line.quantity)
                data[f"lines-{i}-price"] = f"{line.price:.2f}"
                data[f"lines-{i}-line_total"] = f"{line.line_total:.2f}"
            else:
                data[f"lines-{i}-associate"] = ""
                data[f"lines-{i}-article"] = ""
                data[f"lines-{i}-quantity"] = ""
                data[f"lines-{i}-price"] = ""
                data[f"lines-{i}-line_total"] = "0.00"
        for i in range(len(lines), 10):
            for k in ("associate", "article", "quantity", "price"):
                data[f"lines-{i}-{k}"] = ""
            data[f"lines-{i}-line_total"] = "0.00"
        return data

    def test_edit_blanking_existing_line_deletes_it(self):
        """Blank all values on an existing line (Clear button) and save → the line is deleted."""
        txn = self._make_transaction_with_line()
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post(f"/transactions/{txn.id}/edit",
                              self._blank_line_data(txn), HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        txn.refresh_from_db()
        self.assertEqual(txn.lines.count(), 0)

    def test_edit_blanking_one_of_two_lines_deletes_only_it(self):
        """Blanking a single line of an existing transaction leaves the other lines intact."""
        txn = Transaction.objects.create(associate=self.associate, method="cash", amount=130)
        TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.article,
            quantity=1, price=80, line_total=80,
        )
        art2 = _make_article("Second article", price=50)
        TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=art2,
            quantity=1, price=50, line_total=50,
        )
        kept = txn.lines.get(article=art2)
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post(f"/transactions/{txn.id}/edit",
                              self._blank_line_data(txn, kept_lines=(kept,)),
                              HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        txn.refresh_from_db()
        lines = list(txn.lines.all())
        self.assertEqual([line.article_id for line in lines], [art2.id])


# ---------- counselor discount line_total ----------

class TransactionSignalTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.counselor = _make_associate("Csl", membership_type="counselor", active=True,
                                         birth_date=date(1965, 1, 1))
        cls.article = _make_article("Presciistica", price=80, category="skipass")
        cls._discount_article = _make_article("Sconto consigliere", price=0, category="discount")
        # Signal unconditionally looks these up by name
        _tessera_articles()

    def test_counselor_discount_line_has_line_total(self):
        """Auto-created counselor discount TransactionLine must have line_total set."""
        data = _formset_data(self.counselor.id, self.article.id, price=80)
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            Client().post("/transactions/add/", data, HTTP_HOST="localhost")
        txn = Transaction.objects.order_by("-id").first()
        discount = txn.lines.filter(article=self._discount_article).get()
        self.assertIsNotNone(discount.line_total)
        self.assertEqual(discount.line_total, -40)
