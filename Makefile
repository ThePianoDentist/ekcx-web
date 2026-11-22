.PHONY: setup run db-upgrade db-backfill db-ingest test

setup:
	uv sync --extra dev

run:
	uv run uvicorn main:app --reload

db-upgrade:
	uv run alembic upgrade head

db-backfill:
	uv run python scripts/backfill_season.py

db-ingest:
	uv run python scripts/ingest_season_from_db.py

test:
	uv run pytest
