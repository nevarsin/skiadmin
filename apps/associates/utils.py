from datetime import date, timedelta
from django.utils.translation import gettext as _

def is_minor(birth_date):
    """Returns True if the person is under 18 years old, False otherwise."""
    today = date.today()
    age_18 = birth_date + timedelta(days=18 * 365.25)  # Approximate leap years
    return today < age_18

def send_membership_card_via_email(request, associate):
    """
    Generate a receipt PDF and send it via email.
    """
    from django.template.loader import render_to_string    
    from django.core.mail import EmailMultiAlternatives
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
    HTML(string=html_string,base_url=request.build_absolute_uri('/')).write_pdf(pdf_file)
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