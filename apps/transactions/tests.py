from datetime import date
from unittest import mock

from django.contrib.messages import get_messages
from django.test import Client, TestCase

from apps.articles.models import Article
from apps.associates.models import Associate
from apps.subscriptions.models import Subscription
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


def _make_article(name="Presciistica", price=80, category="skipass", type="single", **kw):
    return Article.objects.create(name=name, price=price, category=category, type=type, **kw)


def _formset_data(assoc_id, article_id, *, total_forms=2, qty=1, price=80,
                  article_ids=None, prices=None):
    """POST payload shaped like the browser: filled rows complete, the rest blank.

    line_total is deliberately absent -- it is derived server-side and never posted.
    """
    filled = article_ids or [article_id]
    row_prices = prices or [price] * len(filled)
    data = {
        "associate": str(assoc_id), "method": "cash", "amount": str(qty * sum(row_prices)),
        "lines-TOTAL_FORMS": str(total_forms),
        "lines-INITIAL_FORMS": "0",
        "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
    }
    for i in range(total_forms):
        prefix = f"lines-{i}-"
        if i < len(filled):
            data[f"{prefix}associate"] = str(assoc_id)
            data[f"{prefix}article"] = str(filled[i])
            data[f"{prefix}quantity"] = str(qty)
            data[f"{prefix}price"] = str(row_prices[i])
        else:
            for k in ("associate", "article", "quantity", "price"):
                data[f"{prefix}{k}"] = ""
    return data


def _membership_articles():
    """The pair the Articles panel would flag as the season's membership fees."""
    standard = _make_article("Membership", price=15, category="membership",
                             is_current_membership_fee=True)
    minor = _make_article("Membership kids", price=10, category="membership",
                          is_current_minor_membership_fee=True)
    return standard, minor


# ---------- formset blank-row validation ----------

class TransactionFormsetTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.associate = _make_associate("Std")
        cls.article = _make_article()
        _membership_articles()

    def test_blank_extra_rows_do_not_fail_validation(self):
        """The two unfilled rows rendered by default (browser posts all of them) are discarded."""
        data = _formset_data(self.associate.id, self.article.id)
        fs = TransactionLineFormSet(data)
        self.assertTrue(fs.is_valid(), fs.errors)

    def test_formset_renders_two_initial_rows(self):
        """extra=2 so the user opts into more rows instead of facing ten empty ones."""
        fs = TransactionLineFormSet()
        self.assertEqual(fs.total_form_count(), 2)

    def test_add_with_blank_extra_rows_saves_one_line(self):
        """POST from the browser (2 rows, only row 0 filled) should save one line."""
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
        """Browser-realistic edit POST: existing line + the 2 blank extra rows."""
        txn = self._make_transaction_with_line()
        data = {
            "associate": str(self.associate.id), "method": "cash", "amount": "160.00",
            "lines-TOTAL_FORMS": "3", "lines-INITIAL_FORMS": "1",
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
        }
        line = txn.lines.first()
        for k, v in {"id": str(line.id), "associate": str(self.associate.id),
                     "article": str(self.article.id), "quantity": "2",
                     "price": "80.00"}.items():
            data[f"lines-0-{k}"] = v
        for i in range(1, 3):
            for k in ("associate", "article", "quantity", "price"):
                data[f"lines-{i}-{k}"] = ""
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post(f"/transactions/{txn.id}/edit", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        txn.refresh_from_db()
        self.assertEqual(txn.lines.count(), 1)
        self.assertEqual(txn.lines.first().quantity, 2)

    def _blank_line_data(self, txn, kept_lines=()):
        """Browser-realistic POST that blanks existing lines but preserves hidden id/transaction."""
        lines = list(txn.lines.all().order_by("id"))
        extra = 2
        data = {
            "associate": str(self.associate.id), "method": "cash", "amount": "0.00",
            "lines-TOTAL_FORMS": str(len(lines) + extra),
            "lines-INITIAL_FORMS": str(len(lines)),
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
            else:
                for k in ("associate", "article", "quantity", "price"):
                    data[f"lines-{i}-{k}"] = ""
        for i in range(len(lines), len(lines) + extra):
            for k in ("associate", "article", "quantity", "price"):
                data[f"lines-{i}-{k}"] = ""
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


# ---------- membership fee article chosen from the Articles panel ----------

class MembershipFeeSelectionTests(TestCase):
    """Which membership fee article the signal picks, and when it declines to."""

    def setUp(self):
        self.standard, self.minor = _membership_articles()
        self.skipass = _make_article("Presciistica", price=80, category="skipass")

    def _buy_for(self, birth_date, active=False):
        associate = _make_associate("New", active=active, birth_date=birth_date)
        txn = Transaction.objects.create(associate=associate, method="cash", amount=80)
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            TransactionLine.objects.create(
                transaction=txn, associate=associate, article=self.skipass,
                quantity=1, price=80, line_total=80,
            )
        associate.refresh_from_db()
        return associate, txn

    def _membership_lines(self, txn):
        return [line for line in txn.lines.all()
                if line.article_id in (self.standard.id, self.minor.id)]

    def test_adult_gets_the_standard_article(self):
        associate, txn = self._buy_for(date(1990, 6, 1))
        self.assertEqual([line.article_id for line in self._membership_lines(txn)],
                         [self.standard.id])
        self.assertTrue(associate.active)

    def test_child_aged_14_gets_the_minor_article(self):
        """A birthday already passed this year still counts as 14."""
        born = date(date.today().year - 14, 1, 1)
        _, txn = self._buy_for(born)
        self.assertEqual([line.article_id for line in self._membership_lines(txn)],
                         [self.minor.id])

    def test_child_aged_15_falls_back_to_the_standard_article(self):
        """The old birth-year rule (born >= 2011) would have given this one the
        minor article; a consistent 14 limit does not."""
        born = date(date.today().year - 15, 1, 1)
        _, txn = self._buy_for(born)
        self.assertEqual([line.article_id for line in self._membership_lines(txn)],
                         [self.standard.id])

    def test_minor_flag_is_ignored_for_an_adult(self):
        """Both flags set: the minor one only applies within the age limit."""
        associate, txn = self._buy_for(date(1990, 6, 1))
        self.assertNotIn(self.minor.id, [line.article_id for line in txn.lines.all()])

    def test_expiration_rolls_to_the_next_august_31(self):
        today = date.today()
        expected = date(today.year + 1, 8, 31) if today > date(today.year, 8, 31) \
            else date(today.year, 8, 31)
        associate, _ = self._buy_for(date(1990, 6, 1))
        self.assertEqual(associate.expiration_date, expected)

    def test_active_associate_gets_no_membership_line(self):
        _, txn = self._buy_for(date(1990, 6, 1), active=True)
        self.assertEqual(self._membership_lines(txn), [])

    def test_resaving_a_line_does_not_duplicate_the_membership_line(self):
        associate, txn = self._buy_for(date(1990, 6, 1))
        line = txn.lines.exclude(article_id__in=(self.standard.id, self.minor.id)).get()
        line.save()   # an update, not a creation
        line.save()
        self.assertEqual(len(self._membership_lines(txn)), 1)

    def test_nothing_flagged_leaves_the_associate_inactive(self):
        """Misconfigured Articles panel: charge no fee, do not activate for free."""
        self.standard.is_current_membership_fee = False
        self.standard.save()
        self.minor.is_current_minor_membership_fee = False
        self.minor.save()

        associate, txn = self._buy_for(date(1990, 6, 1))
        self.assertEqual(self._membership_lines(txn), [])
        self.assertFalse(associate.active)

    def test_nothing_flagged_logs_a_warning_instead_of_raising(self):
        self.standard.is_current_membership_fee = False
        self.standard.save()
        with self.assertLogs("apps.transactions.signals", level="WARNING"):
            self._buy_for(date(1990, 6, 1))


# ---------- counselor discount line_total ----------

class TransactionSignalTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.counselor = _make_associate("Csl", membership_type="counselor", active=True,
                                         birth_date=date(1965, 1, 1))
        cls.article = _make_article("Presciistica", price=80, category="skipass")
        cls._discount_article = _make_article("Sconto consigliere", price=0, category="discount")
        _membership_articles()

    def test_counselor_discount_line_has_line_total(self):
        """Auto-created counselor discount TransactionLine must have line_total set."""
        data = _formset_data(self.counselor.id, self.article.id, price=80)
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            Client().post("/transactions/add/", data, HTTP_HOST="localhost")
        txn = Transaction.objects.order_by("-id").first()
        discount = txn.lines.filter(article=self._discount_article).get()
        self.assertIsNotNone(discount.line_total)
        self.assertEqual(discount.line_total, -40)


# ---------- line_total is derived server-side ----------

class TransactionLineTotalTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.associate = _make_associate("Std")
        cls.article = _make_article(price=80)
        _membership_articles()

    def test_line_form_no_longer_exposes_line_total(self):
        """line_total is computed, so it must not be a posted form field."""
        form = TransactionLineFormSet().empty_form
        self.assertNotIn("line_total", form.fields)

    def test_line_total_derived_on_add(self):
        """quantity * price is persisted even though the form never posts line_total."""
        data = _formset_data(self.associate.id, self.article.id, qty=3, price=80)
        self.assertNotIn("lines-0-line_total", data)
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post("/transactions/add/", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        line = Transaction.objects.order_by("-id").first().lines.get()
        self.assertEqual(line.line_total, 240)

    def test_line_total_derived_on_edit(self):
        """Editing quantity re-derives line_total rather than trusting the client."""
        txn = Transaction.objects.create(associate=self.associate, method="cash", amount=80)
        line = TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.article,
            quantity=1, price=80,
        )
        self.assertEqual(line.line_total, 80)
        data = _formset_data(self.associate.id, self.article.id, qty=4, price=80)
        data.update({"lines-TOTAL_FORMS": "3", "lines-INITIAL_FORMS": "1"})
        data["lines-0-id"] = str(line.id)
        data["lines-0-transaction"] = str(txn.id)
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post(f"/transactions/{txn.id}/edit", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        line.refresh_from_db()
        self.assertEqual(line.quantity, 4)
        self.assertEqual(line.line_total, 320)

    def test_posted_line_total_is_ignored(self):
        """A hand-crafted line_total must not be able to inflate a stored line."""
        data = _formset_data(self.associate.id, self.article.id, qty=1, price=80)
        data["lines-0-line_total"] = "9999.00"
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            Client().post("/transactions/add/", data, HTTP_HOST="localhost")
        line = Transaction.objects.order_by("-id").first().lines.get()
        self.assertEqual(line.line_total, 80)


# ---------- dynamic rows ----------

class TransactionDynamicRowTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.associate = _make_associate("Std")
        cls.article = _make_article(price=80)
        cls.second = _make_article("Abbonamento", price=30, category="membership")
        _membership_articles()

    def test_added_rows_are_all_saved(self):
        """Clicking "Add line" grows TOTAL_FORMS; every completed row must persist."""
        data = _formset_data(
            self.associate.id, self.article.id,
            total_forms=5,
            article_ids=[self.article.id, self.second.id, self.article.id],
            prices=[80, 30, 80],
        )
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post("/transactions/add/", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        lines = Transaction.objects.order_by("-id").first().lines.all()
        self.assertEqual(lines.count(), 3)
        self.assertEqual(sum(lines.values_list("line_total", flat=True)), 80 + 30 + 80)

    def test_half_filled_row_still_blocks_save(self):
        """Strict validation: picking an article without an associate is an error."""
        data = _formset_data(self.associate.id, self.article.id)
        data["lines-1-associate"] = ""   # JS filled qty/price, user never chose a beneficiary
        data["lines-1-article"] = str(self.second.id)
        data["lines-1-quantity"] = "1"
        data["lines-1-price"] = "30"
        r = Client().post("/transactions/add/", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 200)
        self.assertIn("associate", str(r.context["formset"].errors[1]))

    def test_delete_flag_removes_existing_line(self):
        """The Remove button flags DELETE on a saved line instead of dropping the row."""
        txn = Transaction.objects.create(associate=self.associate, method="cash", amount=110)
        keep = TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.article, quantity=1, price=80)
        drop = TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.second, quantity=1, price=30)
        data = {
            "associate": str(self.associate.id), "method": "cash", "amount": "80",
            "lines-TOTAL_FORMS": "3", "lines-INITIAL_FORMS": "2",
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
        }
        data.update({
            "lines-0-id": str(keep.id), "lines-0-associate": str(self.associate.id),
            "lines-0-article": str(self.article.id), "lines-0-quantity": "1",
            "lines-0-price": "80", "lines-0-DELETE": "",
            "lines-1-id": str(drop.id), "lines-1-associate": str(self.associate.id),
            "lines-1-article": str(self.second.id), "lines-1-quantity": "1",
            "lines-1-price": "30", "lines-1-DELETE": "on",
        })
        for i in (2,):
            for k in ("associate", "article", "quantity", "price"):
                data[f"lines-{i}-{k}"] = ""
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post(f"/transactions/{txn.id}/edit", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        self.assertEqual([line.id for line in txn.lines.all()], [keep.id])

    def test_manage_page_exposes_row_blueprint(self):
        """manage.html ships an uninitialised __prefix__ blueprint for the JS to clone."""
        html = Client().get("/transactions/add/").content.decode()
        self.assertIn('id="line-template"', html)
        self.assertIn("lines-__prefix__-associate", html)
        self.assertIn('id="add-line"', html)
        self.assertNotIn('name="lines-0-line_total"', html)
        # The blueprint must stay free of select2 markup so cloning is safe.
        blueprint = html.split('<template id="line-template">')[1].split("</template>")[0]
        self.assertNotIn("select2-hidden-accessible", blueprint)


# ---------- duplicate course subscriptions ----------

def _make_course(name, price=100):
    return _make_article(name, price=price, category="skischool", type="course")


class TransactionDuplicateCourseTests(TestCase):
    """unique_subscription_per_associate_article means the second row can never be saved."""

    @classmethod
    def setUpTestData(cls):
        cls.associate = _make_associate("Std")
        cls.course_a = _make_course("Corso A")
        cls.course_b = _make_course("Corso B")
        cls.skipass = _make_article("Presciistica", price=80, category="skipass")
        _membership_articles()

    def _post(self, rows, total_forms=None, url=None):
        data = _formset_data(
            self.associate.id, rows[0][0],
            total_forms=total_forms or len(rows),
            article_ids=[r[0] for r in rows],
            prices=[r[1] for r in rows],
        )
        return Client().post(url or "/transactions/add/", data, HTTP_HOST="localhost")

    def test_same_course_twice_in_one_transaction_is_blocked(self):
        """Both rows are flagged: the operator must merge them before saving."""
        r = self._post([(self.course_a.id, 100), (self.course_a.id, 100)])
        self.assertEqual(r.status_code, 200)
        errors = r.context["formset"].errors
        self.assertIn("article", errors[0])
        self.assertIn("article", errors[1])

    def test_blocked_transaction_is_not_persisted(self):
        """A rejected POST must leave no Transaction and no Subscription behind."""
        self._post([(self.course_a.id, 100), (self.course_a.id, 100)])
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_duplicate_course_message_reaches_the_operator(self):
        """The reason must be rendered, not silently swallowed by a 500."""
        r = self._post([(self.course_a.id, 100), (self.course_a.id, 100)])
        self.assertIn("already has a subscription for Corso A", r.content.decode())

    def test_blocked_save_raises_a_warning_toast(self):
        """The chosen UX: standard warning toast on top of the inline row errors."""
        r = self._post([(self.course_a.id, 100), (self.course_a.id, 100)])
        toasts = [str(m) for m in get_messages(r.wsgi_request)]
        self.assertTrue(any("already has a subscription" in t for t in toasts), toasts)

    def test_course_already_subscribed_elsewhere_is_blocked(self):
        """Buying the same course twice must not attempt a second subscription row."""
        txn = Transaction.objects.create(associate=self.associate, method="cash", amount=100)
        TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.course_a,
            quantity=1, price=100, line_total=100,
        )
        self.assertEqual(Subscription.objects.count(), 1)
        r = self._post([(self.course_a.id, 100)])
        self.assertEqual(r.status_code, 200)
        self.assertIn("article", r.context["formset"].errors[0])
        self.assertEqual(Subscription.objects.count(), 1)

    def test_resaving_own_course_line_is_not_a_false_positive(self):
        """The line that already owns the subscription may be re-saved unchanged."""
        txn = Transaction.objects.create(associate=self.associate, method="cash", amount=100)
        line = TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.course_a,
            quantity=1, price=100, line_total=100,
        )
        self.assertEqual(Subscription.objects.count(), 1)
        data = _formset_data(self.associate.id, self.course_a.id, price=100)
        data.update({"lines-TOTAL_FORMS": "2", "lines-INITIAL_FORMS": "1"})
        data["lines-0-id"] = str(line.id)
        data["lines-0-transaction"] = str(txn.id)
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post(f"/transactions/{txn.id}/edit", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)

    def test_distinct_courses_in_one_transaction_are_allowed(self):
        r = self._post([(self.course_a.id, 100), (self.course_b.id, 120)])
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Subscription.objects.count(), 2)

    def test_repeating_a_non_course_line_is_allowed(self):
        """Only courses are subscription-bound; two skipasses are a normal sale."""
        r = self._post([(self.skipass.id, 80), (self.skipass.id, 80)])
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Transaction.objects.order_by("-id").first().lines.count(), 2)

    def test_deleting_the_duplicate_row_lets_the_save_through(self):
        """Marking the second course row DELETE resolves the conflict."""
        txn = Transaction.objects.create(associate=self.associate, method="cash", amount=200)
        keep = TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.course_a,
            quantity=1, price=100, line_total=100,
        )
        drop = TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.course_b,
            quantity=1, price=100, line_total=100,
        )
        data = {
            "associate": str(self.associate.id), "method": "cash", "amount": "100",
            "lines-TOTAL_FORMS": "2", "lines-INITIAL_FORMS": "2",
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
            "lines-0-id": str(keep.id), "lines-0-associate": str(self.associate.id),
            "lines-0-article": str(self.course_a.id), "lines-0-quantity": "1",
            "lines-0-price": "100",
            "lines-1-id": str(drop.id), "lines-1-associate": str(self.associate.id),
            "lines-1-article": str(self.course_b.id), "lines-1-quantity": "1",
            "lines-1-price": "100", "lines-1-DELETE": "on",
        }
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post(f"/transactions/{txn.id}/edit", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        self.assertEqual([l.id for l in txn.lines.all()], [keep.id])

    def test_swapping_two_course_articles_does_not_crash(self):
        """Regression: the old bulk update() raised IntegrityError here (HTTP 500)."""
        txn = Transaction.objects.create(associate=self.associate, method="cash", amount=220)
        first = TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.course_a,
            quantity=1, price=100, line_total=100,
        )
        second = TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.course_b,
            quantity=1, price=120, line_total=120,
        )
        data = {
            "associate": str(self.associate.id), "method": "cash", "amount": "220",
            "lines-TOTAL_FORMS": "2", "lines-INITIAL_FORMS": "2",
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
            "lines-0-id": str(first.id), "lines-0-associate": str(self.associate.id),
            "lines-0-article": str(self.course_b.id), "lines-0-quantity": "1",
            "lines-0-price": "120",
            "lines-1-id": str(second.id), "lines-1-associate": str(self.associate.id),
            "lines-1-article": str(self.course_a.id), "lines-1-quantity": "1",
            "lines-1-price": "100",
        }
        with mock.patch("apps.associates.utils.send_membership_card_via_email"):
            r = Client().post(f"/transactions/{txn.id}/edit", data, HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 2)

    def test_signal_alone_survives_a_swapped_article(self):
        """Defence in depth: the signal must not raise even without formset validation."""
        txn = Transaction.objects.create(associate=self.associate, method="cash", amount=220)
        first = TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.course_a,
            quantity=1, price=100, line_total=100,
        )
        TransactionLine.objects.create(
            transaction=txn, associate=self.associate, article=self.course_b,
            quantity=1, price=120, line_total=120,
        )
        first.article = self.course_b
        first.save()   # would previously raise IntegrityError
        self.assertEqual(Subscription.objects.count(), 2)
