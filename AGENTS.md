# AGENTS.md

Django 5.2 app (Sci Club Tarcento membership admin). No CI, no lint/formatter/typecheck config, no Makefile — `manage.py` is the only tooling.

## Layout
- `app/` = Django project config (`settings.py`, `urls.py`). Feature apps live in `apps/<name>/` and are imported as `apps.<name>`, never bare `<name>`.
- Global templates in `templates/`; per-app templates under each app. Root `static/` is both `STATIC_URL` and `STATIC_ROOT`; `media/` holds uploads.
- Standalone scripts at repo root: `googlepass.py`, `getgooglepassclass.py`, `create_googlePassClass.py` (Google Wallet testing), `mailtemplate.mjml` (receipt design source, not referenced in code).

## Environment (required)
`app/settings.py` reads everything from env vars via django-environ; the module import fails without them. `app/.env.example` is the full set (SECRET_KEY, DATABASE_*, SERVERNAMES, EMAIL_*, WALLET_*, BASE_URL).
- `environ.Env.read_env()` (this django-environ version) resolves `.env` next to the **calling module** — i.e. `app/.env` — regardless of CWD. So keep your local vars in `app/.env` (or export them); do not rely on a root `.env` being read.
- `WALLET_WALLPAPER_URL` is read in `apps/associates/utils.py:71` but missing from `.env.example` — wallet pass generation KeyErrors without it.
- `ALLOWED_HOSTS`/`SERVERNAMES` come from env: hitting the app via `testserver` (Django test client outside the test runner) raises `DisallowedHost`; unit tests work because the runner appends `testserver`.

## Database
- Postgres only (psycopg2). Even `manage.py test` needs a reachable Postgres (Django creates the test DB).
- Dev Postgres: `docker compose -f docker-compose-dev.yaml up db` → host port **5433**, creds `user`/`password`, db `ski_club`. For local dev use `DATABASE_HOST=localhost, DATABASE_PORT=5433`; `.env.example`'s `db`/`5432` is only valid on the compose network.
- `dbdata*/` (data volumes) and `*.tar.gz` dumps are gitignored.

## Migrations
- `migrations/` dirs are gitignored — migration files are NOT in git (verified via `git check-ignore`). Fresh clones have none; new/changed migrations don't appear in `git status`, commit them with `git add -f`.
- The Docker entrypoint runs `migrate` then `manage.py runserver` on every start — that's the dev server, gunicorn is unused despite being in requirements.

## Verification
```bash
python manage.py test                        # whole suite
python manage.py test apps.associates        # one app
python manage.py test apps.associates.tests.test_views.AssociateViewsTests
```
Django `TestCase` only (no pytest config); tests are in `tests.py` or a `tests/` package.

## Business logic is in signals — hardcoded, don't "clean up"
Saving a `TransactionLine` triggers `apps/transactions/signals.py` and `apps/subscriptions/signals.py`:
- Hardcoded article names/values: `Sconto consigliere` (-50% for `counselor` members), `Tessera ragazzi 2025/2026` / `Tessera 2025/2026` (auto-inserted for inactive associates; minor threshold = birth year >= 2011). Expiration = next Aug 31.
- For an inactive associate with an email, saving a line **sends a real email** with a weasyprint PDF + Google Wallet pass, needing `auth.json` (service account) in CWD plus `WALLET_*` env. Tests touching TransactionLine must mock `apps.associates.utils.send_membership_card_via_email` and set `EMAIL_BACKEND` to something non-SMTP.

## PDFs
weasyprint generates receipts (transactions), reports (reports), membership cards. Needs pango system libs (Dockerfile installs `libpango-1.0-0`, `libpangoft2-1.0-0`); on NixOS run `nix-shell -p python313Packages.weasyprint gettext`.

## i18n
en + it, catalogs in root `locale/`. After touching translatable strings: `django-admin makemessages --all` → edit `locale/it/LC_MESSAGES/django.po` → `django-admin compilemessages` (gettext binaries required).

## Deploy & secrets
- Production stack is `deploy/docker-compose.yaml` (swag proxy + postgres + `stefanochittaro/skiadmin` image); `deploy/` contains real prod secrets (ACME/DNS creds, nginx basic-auth `.htpasswd`).
- Untracked root files (`auth.json`, `.htpasswd`, `.venv/`, `media/`, `deploy/`, root `.env`) are secrets/artifacts — never commit or echo them.