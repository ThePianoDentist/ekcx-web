# PRD: SQLite models (#5, #9–#12)

## Problem

Results and standings are files and generated HTML. There is no shared schema for events, participants, results, or admin users.

## Outcome

- SQLite schema via SQLAlchemy 2.0 and Alembic under vertical slices.
- Public site unchanged; still serves static/file data until ingest (#13).
- DNS dropped on parse; DNF kept with zero points.

## Scope

In: `User`, `Event`, `Club`, `Participant`, `ClubMembership`, `NameNormalisation`, `Result`, `Standing`, `EventPoints`, `ClubStanding`, `ClubCategoryPoints`, migrations, model tests.

Out: admin UI, auth, CSV→DB load.

## Context

Issues #5, #9, #10, #11, #12. Branch `5-sqlite-models` off `staging`.