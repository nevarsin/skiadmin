from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from django.conf import settings


def generate_pdf(request, template_src, context_dict, filename="report.pdf"):
    context_dict = context_dict.copy()
    context_dict["CURRENCY_SYMBOL"] = getattr(settings, "CURRENCY_SYMBOL", "€")
    html_string = render_to_string(template_src, context_dict)    
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
