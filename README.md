# ekcx-web

[ekcx.co.uk](https://ekcx.co.uk) — East Kent Cyclocross website

## Overview

**Current state:** Everything is static. No database. CSV for each race is manually copied into the results folder. Then a script inside `scripts` is run, which calculates the standings and updates the static HTML for the standings page.

**Short term plan:** Move to a database, and add an admin interface which allows admins to add events and upload results.

**Long term plan:** Build an API and let multiple leagues use this admin interface and system.

**Most common problems/challenges:** People's names are slightly different between rounds. They need normalizing, noting that "person A and person B are actually the same person". This is impossible to do automatically with 100% accuracy, so part of the admin interface will be to allow admins to declare these normalisations, as well as suggest ones they may have missed.

Layout: [docs/architecture.md](docs/architecture.md) (vertical slices: data / domain / interfaces per feature).

Workflow: [docs/development.md](docs/development.md) (branches, PRDs, PRs).

## Infra

```
┌─────────────┐
│  webserver  │
└─────────────┘
```

- Currently just a single-instance VPS on DigitalOcean. That will be sufficient for a long time.
  - No dev/staging site yet, but with so few dependencies, it's very easy to test locally.
- No database server yet. We'll stick with SQLite whilst in development, but add a Postgres DB instance when ready.
- Configuration files the server needs live in `/conf`. We use nginx as a reverse-proxy in front of the Python server. We use systemd for running the webserver.
- Production secrets (API keys, session secret): `/etc/ekcx/environment`, managed on the VPS with `sudo ./scripts/server-ekcx-env.sh` after `git pull` (see script help).
- Certbot renews `ekcx.co.uk` via webroot (`/usr/share/nginx/html`). Nginx must serve `/.well-known/acme-challenge/` from that path on both HTTP and HTTPS; do not redirect or proxy it to the app. Automatic renewal is already handled by `snap.certbot.renew.timer` — do not add a cron job.

## Setup

Install [uv](https://docs.astral.sh/uv/) if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then sync the project (creates `.venv` and installs dependencies):

```bash
make setup
```

Local secrets live in repo-root `.env` (gitignored). Copy the template and fill in values:

```bash
cp .env_sample .env
# or migrate from local/shell.env:
./local/setup-env.sh
```

The app, Alembic, and `scripts/backfill_season.py` load `.env` automatically. Shell tools (`make`, one-off commands) still see vars if you export them once per session:

```bash
set -a && source .env && set +a
```

Or add that `source` to your shell config for this repo.

Or directly:

```bash
uv sync
```

## Run

```bash
make run
```

Or:

```bash
uv run uvicorn main:app --reload
```

The server will be available at http://localhost:8000

## Database

SQLite schema is managed with Alembic. The default file is `var/ekcx.sqlite3` (override with `EKCX_DB_PATH`). The public site still reads CSV/JSON by default; database standings use `?source=db`.

```bash
make db-upgrade
```

Or:

```bash
uv run alembic upgrade head
```

`make db-backfill` loads the current season (2026 rounds 1–2) into that file: one `result_exports` row per CrossMgr file on disk (licence columns stripped to CSV text), then parses **ingested** exports into `results`/standings the same way admin confirm does. `qa-*` files under `results/` are ignored. You need the real exports on disk, including round 1 **Elite Women** (`*Elite Women*.xlsx` or `.csv`). It then checks against `templates/standings/2026/`. Round 3 is left out. On staging, run `./scripts/backfill_staging_db.sh` from the app root after `results/2026/{1,2}` is present. Set `EKCX_DB_PATH` to choose the file; staging and production each have their own.

For 2026 standings, the default is still the static HTML. Add `?source=db` to read the same tables from SQLite, e.g. `/standings/2026/v40?source=db`.

## Admin

Set `EKCX_SESSION_SECRET` in `.env` (see Setup above). `./local/setup-env.sh` can generate one.

Create an admin (email is the username; password is printed once — send it to them out of band):

```bash
make db-upgrade
uv run python -m app.users.interfaces.scripts.create_admin you@example.com
```

Log in at `/admin/login` (lands on `/admin/` after sign-in). All `/admin/*` routes except login and logout require a session.

Result uploads: `/admin/results/` lists CrossMgr exports for a season; each filename links to that file’s standings page. `/admin/results/upload` accepts `.csv`/`.xlsx`. The round defaults to one past the latest round that already has a file. A different file for the same race in that round is rejected; replacing the same filename of an ingested export still asks first. Confirming refreshes parsed results and standings from all `result_exports` for that season. `make db-ingest` runs the same refresh without a new upload. Override the results directory with `EKCX_RESULTS_ROOT` (default: repo `results/`).
