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

## Business logic is in signals (counselor discount is still hardcoded)
Saving a `TransactionLine` triggers `apps/transactions/signals.py` and `apps/subscriptions/signals.py`:
- Counselor discount is still hardcoded: `Sconto consigliere` (-50% for `counselor` members). The membership-fee article is NOT hardcoded: it's whichever `Article` has `is_current_membership_fee`, or `is_current_minor_membership_fee` for members aged <= `MINOR_MEMBERSHIP_MAX_AGE` (14), both set from the Articles panel. Expiration comes from the membership-expiry setting below.
- For an inactive associate with an email, saving a line **sends a real email** with a weasyprint PDF + Google Wallet pass, needing `auth.json` (service account) in CWD plus `WALLET_*` env. Tests touching TransactionLine must mock `apps.associates.utils.send_membership_card_via_email` and set `EMAIL_BACKEND` to something non-SMTP.

## Membership expiry
- The policy is a DB setting (existing `apps.core.models.Settings` key/value store, editable at `/settings/`), read by `membership_expiration()` in `apps/associates/utils.py`. Both `Associate.save()` (on creation) and the membership signal use it.
  - `membership_expiry_mode` = `fixed` (default) or `rolling`.
  - `fixed` → next occurrence of `membership_expiry_fixed_date` (`MM-DD`, default `08-31`).
  - `rolling` → `membership_expiry_rolling_years` (default `1`) calendar years from today.
  - Malformed/unknown values fall back to fixed `08-31`; the helper never raises. Seeded by `apps/core/migrations/0002_seed_membership_expiry_settings.py` (gitignored — `git add -f`).
- `manage.py deactivate_expired_memberships` deactivates `active=True, expiration_date < today` (strict; valid through the expiry date) and resets `card_sent` so the next season re-sends the card. Options `--dry-run` and `--today YYYY-MM-DD`; uses `timezone.localdate()`. Intended to run daily via a host cron in prod.

## Health certificates
- Medical certificates live on `Associate`, not `Subscription` (one per member, shared across activity trunks). Fields: `health_certificate_file`, `health_certificate_expiry_date`, `health_certificate_reminder_sent`. Historical Subscription rows were copied over by `apps/subscriptions/migrations/0002_copy_certifications_to_associates.py`, then the Subscription columns were dropped in `0003`.
  - `apps/subscriptions/migrations/0001_initial.py` hardcodes `upload_to='subscription_certifications/'` instead of the (now deleted) `subscription_certification_upload_to` helper. Do **not** "restore" the helper — deleting that line breaks migration loading.
- Helpers all in `apps/associates/utils.py`: `health_certificate_warn_days()`, `health_certificate_upload_to()` (path `health_certificates/<upload YYYYMMDD>/HealthCertificate_<First>_<Last>_<expiry YYYYMMDD|noexp><ext>` — folder is the upload day, filename carries the expiry; extension is preserved since members send pdf/jpg/jpeg), `health_certificate_status()` (returns a machine code `valid`/`expiring`/`expired`/`missing` + `days_left` — do **not** translate the code, the templates do), and `health_certificate_file_name()` (stored path, or `""`).
- `health_certificate_warn_days` is a DB setting (default `15`), same `apps.core.models.Settings` store as the membership-expiry keys.
- `apps/associates/signals.py` has a `pre_save` that re-arms `health_certificate_reminder_sent` whenever the file or expiry date changes, so a re-upload gets a fresh warning.
- `manage.py notify_health_certificate_expiry` emails members who are subscribed to an article with `certification_required=True` when their certificate is expiring or expired, then clears the certificate fields for the expired ones (the file on disk is **not** deleted). Options `--dry-run` and `--today YYYY-MM-DD`; uses `timezone.localdate()`. Expiry is strict (`< today`), so a certificate is valid *through* its expiry date.
  - Re-running is safe, so a missed day costs one day of reminders rather than a stuck job: `health_certificate_reminder_sent` suppresses repeat warnings, expired certificates are cleared after their notification, a member with no reachable address is skipped with a warning instead of aborting the run, and one failing mailbox does not stop the others.
- **Daily cron (host, run as the user in the `docker` group).** Container name is `skiadmin` in both `deploy/docker-compose.yaml` and the root `docker-compose.yaml`, so the line is the same either way. The image sets `WORKDIR /app`, so no path is needed for `manage.py`.
  ```cron
  7 7 * * * /usr/bin/docker exec -T skiadmin python manage.py notify_health_certificate_expiry >> /var/log/skiadmin-certificates.log 2>&1
  17 7 * * * /usr/bin/docker exec -T skiadmin python manage.py deactivate_expired_memberships >> /var/log/skiadmin-certificates.log 2>&1
  ```
  Four things that will bite otherwise:
  - **`-T` is mandatory.** Plain `docker exec` allocates a TTY and cron has none, so the job dies with `the input device is not a TTY`.
  - **Absolute `/usr/bin/docker`.** cron runs with a minimal `PATH` (`/usr/bin:/bin`).
  - **`:07`/`:17`, not `:00`.** Every other cron job on the host fires on the hour; an odd minute avoids queueing behind backups.
  - **Redirect to a file, and pre-create it.** cron only mails output if a MTA is installed, which usually isn't on a small VPS — without a log these fail silently. But a non-root cron user cannot create files in `/var/log`, and if the redirect can't be opened the command never runs at all:
    ```bash
    sudo touch /var/log/skiadmin-certificates.log && sudo chown "$USER" /var/log/skiadmin-certificates.log
    ```
    Add a `logrotate` entry or the file grows forever. (Use a path in `$HOME` instead if you'd rather not touch `/var/log`.)
  Two more worth knowing:
  - Smoke-test after any image bump: `docker exec -T skiadmin python manage.py notify_health_certificate_expiry --dry-run`. `Unknown command` means the pinned image predates the feature (`deploy/` pins `:0.2`, the root file `:0.3.0`) — rebuild and bump the tag.
  - The schedule is interpreted in the **host's** local time, but the command always computes `today` as `Europe/Rome` (`TIME_ZONE`). If the host clock isn't Europe/Rome the run can land either side of the club's midnight; shift the hour, or set `CRON_TZ=Europe/Rome` (cronie only — stock Debian cron ignores it).
- Reports: the `subscription` report choice renders the compliance PDF (pick an article, optionally hiding members whose certificate is valid). Both the report and the command match **any** `Subscription` for the article across all seasons, so a former subscriber is still counted — filter by season if that is ever wrong for a club.

## PDFs
weasyprint generates receipts (transactions), reports (reports), membership cards. Needs pango system libs (Dockerfile installs `libpango-1.0-0`, `libpangoft2-1.0-0`); on NixOS run `nix-shell -p python313Packages.weasyprint gettext`.
- **Page geometry comes only from each template's `@page` rule** — `generate_pdf` in `apps/reports/utils.py` calls `write_pdf()` with no arguments. To change orientation or size, edit the template, not the view.
- **The image needs fonts.** `fonts-liberation` is installed so `Arial` resolves to metric-compatible Liberation Sans. Without it fontconfig silently substitutes DejaVu Sans, which is ~8% wider and makes tables lay out differently from local dev. If you ever drop that package, check `docker run --rm --entrypoint fc-match <image> Arial` before trusting a local rendering.
- **Tables that can overflow need `table-layout: fixed` + a `<colgroup>`.** Certificate filenames are long unbroken tokens (underscores, no spaces), so with the default auto layout the column just grows to fit and pushes the table off the A4 edge — measured 17mm of clipping before the fix. `overflow-wrap`/`word-break` on the cell does nothing on its own, because the cell is never constrained; only once the layout is fixed does the token actually break. The `subscription` report uses widths 21/9/33/15/22%.
- To check a report fits, render it and measure the widest `TableBox` against the page width — the page-width `html`/`PageBox` boxes are always exactly 210mm, so a naive "widest box" check silently passes on a clipped table.

## i18n
en + it, catalogs in root `locale/`. After touching translatable strings: `django-admin makemessages --all` → edit `locale/it/LC_MESSAGES/django.po` → `django-admin compilemessages` (gettext binaries required).
- `makemessages` fuzzy-matches new msgids onto similar existing ones, and the hits are often **wrong** (e.g. `Expiring` → `Data scadenza`, which means "expiry date"). Fuzzy entries are ignored by gettext, so a bad match silently falls back to English rather than shipping garbage — but always review `#, fuzzy` blocks you just created and drop the flag once the translation is right.
- Translate `msgid`s on machine status codes only in the template, not in Python: `health_certificate_status()` returns the raw code and the template runs `{% trans %}`.

## Deploy & secrets
- Production stack is `deploy/docker-compose.yaml` (swag proxy + postgres + `stefanochittaro/skiadmin` image); `deploy/` contains real prod secrets (ACME/DNS creds, nginx basic-auth `.htpasswd`).
- Untracked root files (`auth.json`, `.htpasswd`, `.venv/`, `media/`, `deploy/`, root `.env`) are secrets/artifacts — never commit or echo them.