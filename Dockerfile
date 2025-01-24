FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY transactions/ transactions/
COPY associates/ associates/
COPY templates/ templates/
COPY manage.py .

EXPOSE 8000

# CMD ["python", "manage.py", "migrate", "&&", "python", "manage.py", "runserver", "0.0.0.0:8000"]
CMD python manage.py migrate && \
    python manage.py runserver 0.0.0.0:8000