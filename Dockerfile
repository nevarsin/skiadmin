FROM python:3.13-slim
# fonts-liberation gives us Liberation Sans, which is metric-compatible with
# Arial. Without it fontconfig silently substitutes the wider DejaVu Sans, and
# the PDF reports lay out differently from local dev (see AGENTS.md).
# --error-on=any: without it a failed index download (e.g. no DNS in the build
# network) only warns, and install then reports every package as missing.
RUN apt-get update --error-on=any && apt-get install -y build-essential libglib2.0-0t64 libpango-1.0-0 libpangoft2-1.0-0 fonts-liberation && rm -rf /var/lib/apt/lists/*

COPY --chmod=755 <<EOT /entrypoint.sh
#!/usr/bin/env bash
set -e
python manage.py migrate && \
exec python manage.py runserver 0.0.0.0:8000
EOT

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY apps/ apps/
COPY templates/ templates/
COPY locale/ locale/
COPY static/ static/

COPY manage.py .

EXPOSE 8000
RUN useradd -m skiadmin
USER skiadmin

ENTRYPOINT ["/entrypoint.sh"]
