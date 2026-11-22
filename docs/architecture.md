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
  mail/{data,domain,interfaces/scripts}
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

Today: public pages still read CSV/JSON/HTML. SQLite models live under each slice’s `data/`; Alembic manages schema. `make db-backfill` seeds events, `result_exports`, and parsed tables from disk (2026 rounds 1–2). Admin upload saves `result_exports` as `pending_review`, runs rider/club name checks (stored cross-season rules + new similarity suggestions), then ingests only after confirm/accept-all; confirm rebuilds `results`/standings from **ingested** exports only. `rider_name_rules` / `club_name_rules` persist across seasons. Standings for 2026: `?source=db`; default static HTML. Target: move domain/data into slice packages as we touch each area.

## SQLite

Stay SQLite-compatible.
