.PHONY: setup run db-upgrade db-backfill test

setup:
	uv sync --extra dev

run:
	uv run uvicorn main:app --reload

db-upgrade:
	uv run alembic upgrade head

db-backfill:
	uv run python scripts/backfill_season.py

test:
	uv run pytest
