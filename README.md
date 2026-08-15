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

## Setup

Install [uv](https://docs.astral.sh/uv/) if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then sync the project (creates `.venv` and installs dependencies):

```bash
make setup
```

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
