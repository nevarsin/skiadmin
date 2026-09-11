import re
from datetime import timedelta

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from weasyprint import HTML

TIME_RE = re.compile(r"^(?P<minutes>\d+):(?P<seconds>\d{2})\.(?P<hundredths>\d{2})$")


def parse_time(text):
    """Parse 'M:SS.cc' (minutes:seconds.hundredths) into a timedelta. None if blank/invalid."""
    if not text:
        return None
    match = TIME_RE.match(str(text).strip())
    if not match:
        return None
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    hundredths = int(match.group("hundredths"))
    return timedelta(minutes=minutes, seconds=seconds, microseconds=hundredths * 10000)


def format_time(duration):
    """Render a timedelta as 'M:SS.cc'. Returns '' for None."""
    if duration is None:
        return ""
    total_hundredths = int(round(duration.total_seconds() * 100))
    minutes, rest = divmod(total_hundredths, 6000)
    seconds, hundredths = divmod(rest, 100)
    return f"{minutes}:{seconds:02d}.{hundredths:02d}"


def rank_participants(participants):
    """
    Build ranked result rows ordered by race_time ascending.
    Equal times share the same position; missing times are listed
    last with position/time shown as DNF.
    """
    rows = []
    position = 0
    index = 0
    previous = None
    for p in participants:
        if p.race_time is None:
            rows.append(
                {"position": _("DNF"), "time": _("DNF"), "participant": p}
            )
            continue
        index += 1
        if p.race_time != previous:
            position = index
            previous = p.race_time
        rows.append(
            {"position": position, "time": format_time(p.race_time), "participant": p}
        )
    return rows


def render_pdf(request, template_src, context_dict, filename="report.pdf"):
    html_string = render_to_string(template_src, context_dict)
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response