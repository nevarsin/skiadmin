# Ski Admin

<p align="center">
    <img src="./apps/associates/static/images/logo.png" width="250" />
</p>

## State
The app is in a semifunctional state with the following basic features:
- Associates management
- Transactions/Articles management
- Subscriptions management
- Reports for Associates and Transactions (hardcoded layout)
I'm currently rushing to release features for the upcoming Ski season. Polishing and UI refactoing will come next year

## Roadmap
Check TODO.md

## Purpose / Scopo

This application is designed to manage a ski club association's members (associates) and their transactions (e.g., ski pass purchases, card renewals). It allows the club to maintain personal data of members and transaction records efficiently, while being easy to deploy and extend.

Questa applicazione è progettata per gestire i membri (associati) di un'associazione sciistica e le loro transazioni (ad esempio, acquisti di skipass, rinnovi di tessere). Permette all'associazione di mantenere i dati personali dei soci e i registri delle transazioni in modo efficiente, ed è facile da implementare ed estendere.

## License ![License](https://img.shields.io/github/license/widelands/widelands.svg?color=blue)

GPL v2+. Some assets are released under various Creative Commons licenses

## Quick Start

To run the application using Docker, follow these instructions.

### Requirements
- Docker installed on your machine.
- Docker Compose installed (comes with Docker Desktop on most platforms).

### Steps
1. Clone this repository:
   ```bash
   git clone https://github.com/nevarsin/skiclub-ng.git
   cd skiclub-ng ```
2. Rename app/.env.sample to .env and fill with your db connection details
3. (If using embedded Postgres) Set up your Postgres auth details in 'docker-compose.yaml'
4. Build image and spin up containers:
    ```bash
    docker compose build
    docker compose up -d
    ```

## Development setup
For local development and testing, follow these steps.

### Requirements
* Python 3.8+ installed on your machine.
* PostgreSQL (or Docker for PostgreSQL container).

### Steps
1. Clone this repository:
   ```bash
   git clone https://github.com/nevarsin/skiclub-ng.git
   cd skiclub-ng ```
2. Setup a Python virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3. Install deps:
    ```bash
    pip install -r requirements.txt
    ```
4. Rename .env.sample to .env and fill with your db connection details:
    ```bash
    mv .env.sample app/.env
    ```
5. Apply migrations
    ```bash
    python manage.py migrate
    ```
6. (Optional) Create a superuser to access Django admin:
    ```bash
    python manage.py createsuperuser
    ```
7. Run development server
    ```bash
    python manage.py runserver
    ```

## Translations
In order to add further languages:

`django-admin makemessages -lt YOURLOCALE`

Then edit locale\YOURLOCALE\LC_MESSAGES\django.po adding your translated strings.

After that:
`django-admin compilemessages`

And your good to run app again with:
`python manage.py runserver`

## Notes for NixOS
Since NixOS doesn't support global libraries location, use the following to start a nix-shell with what's missing
`nix-shell -p python313Packages.weasyprint gettext`