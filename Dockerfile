FROM python:3.13-slim
RUN apt update && apt install -y build-essential libgobject-2.0-0 libpango-1.0-0 libpangoft2-1.0-0 && rm -rf /var/lib/apt/lists/*

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
COPY transactions/ transactions/
COPY associates/ associates/
COPY subscriptions/ subscriptions/
COPY transactions/ transactions/
COPY articles/ articles/
COPY templates/ templates/
COPY locale/ locale/
COPY static/ static/
COPY core/ core/

COPY manage.py .

EXPOSE 8000
RUN useradd -m skiadmin
USER skiadmin

ENTRYPOINT ["/entrypoint.sh"]