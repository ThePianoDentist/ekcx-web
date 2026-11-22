"""Build review page context for a single result export."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from sqlalchemy.orm import Session

from app.events.data.models import Event
from app.participants.domain.name_normalisation import (
    LoadedRules,
    NameSuggestion,
    load_rules,
    new_suggestions,
    stored_applications,
)
from app.results.data.models import ResultExport
from app.results.domain.collect_exports import collect_results_from_exports
from app.results.domain.ingest_review import ExportNameRows, names_in_csv


@dataclass
class ExportReviewContext:
    export: ResultExport
    event: Event
    stored: List[NameSuggestion]
    suggestions: List[NameSuggestion]


def _touches_export(suggestion: NameSuggestion, export_names: ExportNameRows) -> bool:
    if suggestion.kind == "rider":
        parts = [p.strip() for p in suggestion.source.split(",", 1)]
        if len(parts) != 2:
            return False
        source = (parts[0].upper(), parts[1].upper())
        for last, first in export_names.riders:
            if last.upper() == source[0] and first.upper() == source[1]:
                return True
        return False
    return suggestion.source in export_names.teams


def build_export_review(session: Session, export: ResultExport, year: int) -> ExportReviewContext:
    event = export.event
    if event is None:
        event = session.get(Event, export.event_id)
    all_results = collect_results_from_exports(
        session,
        year,
        extra_export_ids={export.id},
    )
    rules: LoadedRules = load_rules(session)
    stored_all = stored_applications(all_results, rules)
    new_all = new_suggestions(all_results, rules)
    export_names = names_in_csv(export.csv_text)
    stored = [s for s in stored_all if _touches_export(s, export_names)]
    suggestions = [s for s in new_all if _touches_export(s, export_names)]
    return ExportReviewContext(
        export=export,
        event=event,
        stored=stored,
        suggestions=suggestions,
    )