# Architecture

Vertical slices under `app/`. Each slice keeps [Beith-style](https://www.jamesbeith.co.uk/blog/how-to-structure-django-projects/) layers: **data** → **domain** ← **interfaces**.

## Layers (inside a slice)

| Layer | Role | Must not |
|-------|------|----------|
| **data** | SQLite/JSON/file I/O for this feature | Business rules |
| **domain** | Business logic | HTTP, templates, CLI |
| **interfaces** | web / admin / scripts | Own business rules or write DB directly |

`interfaces → domain → data`. Cross-slice: prefer calling the other slice’s **domain**.

## Target layout

```
app/
  results/{data,domain,interfaces/{web,admin,scripts}}
  standings/{data,domain,interfaces/{web,admin,scripts}}
  events/{data,domain,interfaces/{web,admin,scripts}}
  participants/{data,domain,interfaces/{web,admin}}
  users/{data,domain,interfaces/admin}
```

Raw exports stay at repo-root paths (e.g. `results/2025/1/*.csv`). Not inside `app/`.

## Why slices

Admin is near-term: upload results, edit events, declare rider merges. Colocating `admin` with the feature beats a flat global `interfaces/` once several areas get admin screens.

## Examples

- `results` — clean CrossMgr files, build tables; admin upload; script ingest
- `standings` — points rules; public standings page; regen script
- `events` — round metadata; admin CRUD; public event pages
- `participants` — clubs, name normalisations; admin suggestions/confirmations

## Current vs target

Today: public pages still read CSV/JSON/HTML. SQLite models live under each slice’s `data/`; Alembic manages schema. `make db-backfill` loads 2026 rounds 1–2 into the local file (`EKCX_DB_PATH`), including `result_exports` (licence-stripped CSV text per file, for staging ingest). Standings for 2026 can be viewed from that file with `?source=db`; the default stays the static HTML. Older seasons stay static HTML. Target: move domain/data into slice packages as we touch each area.

## SQLite

Stay SQLite-compatible.
