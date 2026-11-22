"""Build the all_results map from stored export CSV text."""

from __future__ import annotations

from collections import defaultdict
from io import StringIO
from typing import Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from app.results.data import repository
from app.results.data.repository import INGEST_STATUS_INGESTED
from app.results.domain.category_from_filename import determine_category_from_filename
from app.results.domain.race_dataframe import prepare_race_dataframe
from scripts.generate_standings_2025 import (
    calculate_points,
    normalize_first_name,
    normalize_name,
)


class IngestError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _rows_from_dataframe(df: pd.DataFrame, round_num: str) -> List[dict]:
    rows: List[dict] = []
    for _, row in df.iterrows():
        gender_val = str(row.get("Gender", "")).strip() if "Gender" in row else ""
        if pd.isna(row["Pos"]):
            position = None
            points = 0
        else:
            position = int(row["Pos"])
            points = calculate_points(position)
        rows.append(
            {
                "round": round_num,
                "position": position,
                "points": points,
                "dnf": position is None,
                "last_name": normalize_name(row["Last Name"]),
                "first_name": normalize_first_name(row["First Name"]),
                "team": str(row["Team"]).strip(),
                "category": str(row["Category"]).strip(),
                "gender": gender_val,
            }
        )
    return rows


def collect_results_from_exports(
    session: Session,
    year: int,
    *,
    extra_export_ids: set[int] | None = None,
) -> Dict[str, Dict[str, List[dict]]]:
    """Returns {category: {round: [result_dict, ...]}} from ingested exports (+ optional extras)."""
    all_results: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
    extras = extra_export_ids or set()

    for export, event in repository.list_exports_for_year(session, year):
        if export.ingest_status != INGEST_STATUS_INGESTED and export.id not in extras:
            continue
        category = determine_category_from_filename(export.filename)
        if category == "skip":
            continue
        if category == "unknown":
            raise IngestError(f"Could not determine category for {export.filename}")

        try:
            df = pd.read_csv(StringIO(export.csv_text))
        except Exception as exc:
            raise IngestError(f"Invalid CSV in {export.filename}: {exc}") from exc

        df = prepare_race_dataframe(df)
        if df.empty:
            continue

        round_num = str(event.round_number)
        all_results[category][round_num].extend(_rows_from_dataframe(df, round_num))

    return all_results