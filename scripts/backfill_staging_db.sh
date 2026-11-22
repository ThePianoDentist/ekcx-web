#!/usr/bin/env bash
# Load 2026 rounds 1–3 (parsed results + licence-stripped raw CSV) into SQLite.
# Run on staging from the app root after result files are on disk, e.g.:
#   cd /home/jdog/ekcx-dev && ./scripts/backfill_staging_db.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export EKCX_DB_PATH="${EKCX_DB_PATH:-${ROOT}/var/ekcx.sqlite3}"
mkdir -p "$(dirname "$EKCX_DB_PATH")"

echo "Database: ${EKCX_DB_PATH}"
uv run alembic upgrade head
exec uv run python scripts/backfill_season.py