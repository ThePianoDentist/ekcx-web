.PHONY: setup run

setup:
	uv sync

run:
	uv run uvicorn main:app --reload
