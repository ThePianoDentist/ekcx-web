.PHONY: setup run db-upgrade test

setup:
	uv sync --extra dev

run:
	uv run uvicorn main:app --reload

db-upgrade:
	uv run alembic upgrade head

test:
	uv run pytest
