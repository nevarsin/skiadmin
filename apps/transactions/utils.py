from io import BytesIO

from django.core.mail import EmailMessage
from django.utils.translation import gettext_lazy as _
from weasyprint import HTML


def send_receipt_via_email(transaction, transaction_lines, to_email):
    """
    Generate a receipt PDF and send it via email.
    """
    from django.template.loader import render_to_string

    # Render the PDF content
    html_string = render_to_string(
        "transactions/receipt.html",
        {"transaction": transaction, "transaction_lines": transaction_lines},
    )

    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(pdf_file)
    pdf_file.seek(0)

    # Build the email
    subject = _("Receipt %(id)s/%(year)s") % {"id": transaction.id, "year": transaction.date.year}
    body = _("Dear %(first_name)s %(last_name)s,\n\nPlease find attached your receipt.\n\nSci Club Tarcento"
    ) % {"first_name": transaction.associate.first_name.title(),"last_name": transaction.associate.last_name.title()}
    email = EmailMessage(subject, body, to=[to_email], cc=['info@sciclubtarcento.it'])
    email.attach(f"receipt_{transaction.id}-{transaction.date.year}.pdf", pdf_file.read(), "application/pdf")    
    email.send()
