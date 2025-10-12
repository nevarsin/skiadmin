from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML

def generate_pdf(template_src, context_dict, filename="report.pdf"):
    html_string = render_to_string(template_src, context_dict)
    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
