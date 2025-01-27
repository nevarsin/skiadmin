# Ski Admin

<p align="center">
    <img src="./associates/static/images/logo.png" width="250" />
</p>

## State
The app is in no way in a working state, it's a work in progress to learn Django and, at the same time, rework the MS Access Management tool our Ski Club is now using for 15 years :D

## Purpose / Scopo

This application is designed to manage a ski club association's members (associates) and their transactions (e.g., ski pass purchases, card renewals). It allows the club to maintain personal data of members and transaction records efficiently, while being easy to deploy and extend.

Questa applicazione è progettata per gestire i membri (associati) di un'associazione sciistica e le loro transazioni (ad esempio, acquisti di skipass, rinnovi di tessere). Permette all'associazione di mantenere i dati personali dei membri e i registri delle transazioni in modo efficiente, ed è facile da implementare ed estendere.

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
2. Rename .env.sample to .env and fill with your db connection details:
    ```bash
    mv .env.sample app/.env
    ```
3. (If using embedded Postgres) Set up your Postgres auth details in 'docker-compose.yaml0
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
