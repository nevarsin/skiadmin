import calendar
import os
from datetime import date, timedelta

from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.translation import gettext as _

def is_minor(birth_date):
    """Returns True if the person is under 18 years old, False otherwise."""
    today = date.today()
    age_18 = birth_date + timedelta(days=18 * 365.25)  # Approximate leap years
    return today < age_18


def _clamped_date(year, month, day):
    """Build a date, clamping the day to the last day of that month (Feb 29 -> 28)."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def _add_years(value, years):
    """Add whole calendar years to a date, clamping Feb 29 to Feb 28 when needed."""
    return _clamped_date(value.year + years, value.month, value.day)


def _next_occurrence(from_date, month, day):
    """The next occurrence of a month/day on or after `from_date`."""
    candidate = _clamped_date(from_date.year, month, day)
    if candidate < from_date:
        candidate = _clamped_date(from_date.year + 1, month, day)
    return candidate


def _parse_month_day(raw, default=(8, 31)):
    """Parse a "MM-DD" string, falling back to `default` when malformed."""
    try:
        month, day = (int(part) for part in str(raw).strip().split("-"))
        if not 1 <= month <= 12 or not 1 <= day <= 31:
            return default
        return month, day
    except (TypeError, ValueError):
        return default


def membership_expiration(from_date=None):
    """Expiration date for a membership starting/renewing on `from_date`.

    The policy is a site setting so the app is reusable by organizations with
    different conventions:

    - `membership_expiry_mode = "fixed"` (default): expires on the next
      occurrence of `membership_expiry_fixed_date` (a recurring "MM-DD").
    - `membership_expiry_mode = "rolling"`: expires `membership_expiry_rolling_years`
      calendar years after `from_date` (i.e. one year from today by default).

    Never raises: an unknown mode falls back to "fixed" and a malformed date to
    "08-31", so a bad setting cannot break member creation.
    """
    from apps.core.models import Settings

    if from_date is None:
        from_date = timezone.localdate()

    mode = str(Settings.get_value("membership_expiry_mode", "fixed") or "fixed").strip().lower()

    if mode == "rolling":
        raw_years = Settings.get_value("membership_expiry_rolling_years", "1")
        try:
            years = int(str(raw_years).strip())
            if years < 1:
                years = 1
        except (TypeError, ValueError):
            years = 1
        return _add_years(from_date, years)

    month, day = _parse_month_day(Settings.get_value("membership_expiry_fixed_date", "08-31"))
    return _next_occurrence(from_date, month, day)


# Fallback when the `health_certificate_warn_days` setting is missing or malformed.
DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS = 15


def health_certificate_warn_days():
    """How many days before expiry the associate gets the renewal reminder.

    A site setting so clubs can pick their own lead time. Never raises: a
    missing or malformed value falls back to
    `DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS`.
    """
    from apps.core.models import Settings

    raw = Settings.get_value("health_certificate_warn_days", str(DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS))
    try:
        days = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS
    return days if days >= 0 else DEFAULT_HEALTH_CERTIFICATE_WARN_DAYS


def health_certificate_upload_to(instance, filename):
    """Upload path for a member's health certificate.

    Keeps certificates in per-day folders so the volume stays browsable, and
    records the expiry date in the filename to make it obvious at a glance.
    The uploaded extension is preserved: members send pdf, jpg and jpeg alike.
    """
    today_str = timezone.now().strftime("%Y%m%d")
    associate_name = f"{instance.first_name}_{instance.last_name}".strip("_")
    exp_date = (
        instance.health_certificate_expiry_date.strftime("%Y%m%d")
        if instance.health_certificate_expiry_date
        else "noexp"
    )
    ext = os.path.splitext(filename)[1] or ".pdf"
    new_filename = f"HealthCertificate_{associate_name}_{exp_date}{ext}"
    return os.path.join("health_certificates", today_str, new_filename)


def health_certificate_file_name(associate):
    """The stored certificate path, or "" when there is no certificate."""
    field = getattr(associate, "health_certificate_file", None)
    if not field:
        return ""
    # Accept plain strings too, so the helper works on unsaved or dict-shaped data.
    return getattr(field, "name", field)


# Verdict codes for a member's health certificate, shared by the associate list,
# the compliance report and the expiry command so they can never disagree.
HEALTH_CERT_VALID = "valid"
HEALTH_CERT_EXPIRING = "expiring"
HEALTH_CERT_EXPIRED = "expired"
HEALTH_CERT_MISSING = "missing"


def health_certificate_status(associate, today=None, warn_days=None):
    """Classify a member's health certificate.

    Returns `(code, days_left)` where `days_left` is None for a missing
    certificate. A certificate expiring *today* is still valid -- it only counts
    as expired once the date has passed, matching how expired memberships are
    handled.

    Reads only already-loaded columns, so this costs no extra queries and is
    safe to call once per row of a list.
    """
    if today is None:
        today = timezone.localdate()
    if warn_days is None:
        warn_days = health_certificate_warn_days()

    if not health_certificate_file_name(associate):
        return HEALTH_CERT_MISSING, None

    expiry = associate.health_certificate_expiry_date
    if expiry is None:
        # A certificate with no recorded expiry cannot be chased, but it was
        # supplied, so it counts as compliant rather than missing.
        return HEALTH_CERT_VALID, None

    days_left = (expiry - today).days
    if days_left < 0:
        return HEALTH_CERT_EXPIRED, days_left
    if days_left <= warn_days:
        return HEALTH_CERT_EXPIRING, days_left
    return HEALTH_CERT_VALID, days_left


def health_certificate_recipients(associate):
    """Addresses to notify about a member's health certificate.

    Minors are the ones most likely to be missing a certificate, so the parent's
    address is included whenever it differs from the member's own.
    """
    recipients = []
    for address in (associate.email, associate.parent_email):
        if address and address not in recipients:
            recipients.append(address)
    return recipients


def send_health_certificate_expiry_email(associate, days_left):
    """Warn a member that their health certificate is about to expire, or has.

    `days_left` is negative for an already-expired certificate.
    """
    expiry = associate.health_certificate_expiry_date
    name = f"{associate.first_name} {associate.last_name}"

    if days_left < 0:
        subject = _("Health certificate expired") % {"name": name.title()}
        body = _(
            """
        <html>
            Dear %(first_name)s %(last_name)s,<br />
            Your health certificate expired on %(expiry_date)s, so you cannot take part in
            activities that require it until you send us a new one.<br />
            You can hand it in at the club office or reply to this email.<br /><br />
            Sci Club Tarcento
        </html>
        """
        ) % {
            "first_name": associate.first_name.title(),
            "last_name": associate.last_name.title(),
            "expiry_date": expiry.strftime("%d/%m/%Y") if expiry else "-",
        }
    else:
        subject = _("Health certificate expiring in %(days)s days") % {
            "name": name.title(),
            "days": days_left,
        }
        body = _(
            """
        <html>
            Dear %(first_name)s %(last_name)s,<br />
            Your health certificate expires on %(expiry_date)s. Please send us a new one
            before then, otherwise you cannot take part in activities that require it.<br /><br />
            Sci Club Tarcento
        </html>
        """
        ) % {
            "first_name": associate.first_name.title(),
            "last_name": associate.last_name.title(),
            "expiry_date": expiry.strftime("%d/%m/%Y") if expiry else "-",
        }

    email = EmailMultiAlternatives(
        subject,
        body,
        to=health_certificate_recipients(associate),
        cc=["info@sciclubtarcento.it"],
    )
    email.attach_alternative(body, "text/html")
    email.send()

def send_membership_card_via_email(associate):
    """
    Generate a receipt PDF and send it via email.
    """
    from django.template.loader import render_to_string    
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    from weasyprint import HTML
    from io import BytesIO


    qr_code = generate_qr(associate.id)
    # Render the PDF content
    html_string = render_to_string(
        "associates/membership_card.html",
        {"associate": associate,
        "qr_code": qr_code}
    )
    
    pass_url = generate_wallet_pass(associate)    

    pdf_file = BytesIO()
    HTML(string=html_string,base_url=f"{settings.BASE_URL}/{settings.STATIC_ROOT}/").write_pdf(pdf_file)    
    pdf_file.seek(0)

    # Build the email
    subject = _("Membership Card %(name)s %(number)s") % {"number": associate.id, "name": f"{associate.first_name} {associate.last_name}"}
    body = _("""
    <html>
        Dear %(first_name)s %(last_name)s,<br />
        Please find attached your membership card <br /> 
        Or, if you have an Android phone, click below <br /><br /> 
        <a href=\"%(pass_url)s\"><img src=\"https://www.sciclubtarcento.it/wp-content/uploads/2025/11/enGB_add_to_google_wallet_add-wallet-badge.png\" 
        alt=\"Add to Google Wallet\"></a><br /><br />
        Sci Club Tarcento
    </html>    
    """
    ) % {"first_name": associate.first_name.title(),"last_name": associate.last_name.title(), "pass_url": pass_url}
    email = EmailMultiAlternatives(subject, body, to=[associate.email], cc=['info@sciclubtarcento.it'])
    email.attach(f"membership_card_{associate.first_name}-{associate.last_name}-{associate.expiration_date}.pdf", pdf_file.read(), "application/pdf")    
    email.attach_alternative(body, "text/html")
    email.send()

    # Set associates card_sent flag to true
    associate.card_sent = True
    associate.save(update_fields=["card_sent"])

    

def generate_wallet_pass(associate):
    import json, time
    import os
    import jwt  # PyJWT
    
    from django.http import JsonResponse    
    from google.oauth2 import service_account
    
    SERVICE_ACCOUNT_FILE = "./auth.json"
    ISSUER_ID = os.environ["WALLET_ISSUER_ID"] # from Wallet console
    PASS_ID = os.environ["WALLET_PASS_ID"]
    LOGO_URL = os.environ["WALLET_LOGO_URL"]
    WALLPAPER_URL = os.environ["WALLET_WALLPAPER_URL"]

    # === STATIC CONF ===
    CLASS_ID = f"{ISSUER_ID}.{PASS_ID}" 
    API_SCOPE = "https://www.googleapis.com/auth/wallet_object.issuer"
    API_URL = f"https://walletobjects.googleapis.com/walletobjects/v1/genericClass"

    # === LOAD SERVICE ACCOUNT ===
    with open(SERVICE_ACCOUNT_FILE, "r", encoding="utf-8") as f:
        sa = json.load(f)

    private_key = sa["private_key"]
    client_email = sa["client_email"]

    # === BUILD PAYLOAD ===
    timestamp = int(time.time())
    object_id = f"{ISSUER_ID}.{associate.id}_{timestamp}"
    
    claims = {
        "iss": client_email,
        "aud": "google",
        "typ": "savetowallet",
        "iat": timestamp,
        "payload": {
            "genericObjects": [
                {
                    "id": object_id,
                    "classId": CLASS_ID,                
                    "cardTitle": {"defaultValue": {"language": "it","value": "Sci Club Tarcento"}},
                    "logo": {"sourceUri": {"uri": LOGO_URL}},
                    "header": { "defaultValue": {"language": "en", "value": f"{associate.first_name} {associate.last_name}"}},
                    "subheader": { "defaultValue": {"language": "en", "value": f"Socio N° {associate.id}"}},
                    "barcode": {"type": "QR_CODE", "value": associate.id},
                    "heroImage": {"sourceUri": {"uri": WALLPAPER_URL}},
                    "textModulesData": [
                        {"header": "Membership", "body": "Active", "id": "membership_status"},
                        {"header": "Expires", "body": str(associate.expiration_date), "id": "expiration"},

                    ],
                }
            ]
        },
    }

    # === SIGN JWT ===
    token = jwt.encode(claims, private_key, algorithm="RS256")

    # === GENERATE WALLET URL ===
    save_url = f"https://pay.google.com/gp/v/save/{token}"
    return(save_url)

def generate_qr(string):
    import qrcode
    import base64
    from io import BytesIO

    # Generate QR code
    qr = qrcode.QRCode()
    qr.add_data(string)
    img = qr.make_image(fill='black', back_color='white')

    # Convert to binary
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return img_str