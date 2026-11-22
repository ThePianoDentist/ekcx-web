from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import joinedload
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from app.db.session import get_session_factory
from app.participants.domain.name_normalisation import (
    build_stored_maps_for_refresh,
    load_rules,
    maps_for_accepted,
    new_suggestions,
    upsert_accepted_suggestions,
)
from app.results.data import repository
from app.results.data.models import ResultExport
from app.results.data.repository import INGEST_STATUS_INGESTED
from app.results.domain.collect_exports import IngestError, collect_results_from_exports
from app.results.domain.exports import ExportError, list_exports_for_season, store_upload
from app.results.domain.ingest_review import (
    ConfirmValidationError,
    apply_maps_to_csv,
    csv_text_diff,
    validate_confirm,
)
from app.results.domain.review_context import build_export_review
from app.standings.domain.refresh_from_exports import refresh_season_from_exports
from app.web.templates import templates

router = APIRouter(tags=["admin-results"])


def _parse_id_list(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    return {v for v in values if v}


@router.get("/", response_class=HTMLResponse)
async def results_index(request: Request, year: int = 2026):
    rows = []
    db_error = None
    factory = get_session_factory()
    session = factory()
    try:
        rows = list_exports_for_season(session, year)
    except OperationalError:
        db_error = "Database not available. Run make db-upgrade and db-backfill."
    finally:
        session.close()
    msg = request.query_params.get("msg")
    return templates.TemplateResponse(
        request=request,
        name="admin/results_index.html",
        context={
            "year": year,
            "rows": rows,
            "msg": msg,
            "db_error": db_error,
        },
    )


@router.get("/exports/{export_id}/download")
async def download_export(export_id: int):
    factory = get_session_factory()
    session = factory()
    try:
        export = repository.get_export(session, export_id)
        if export is None:
            return Response(status_code=404, content="Not found")
        headers = {
            "Content-Disposition": f'attachment; filename="{export.filename}"',
        }
        return Response(
            content=export.csv_text,
            media_type="text/csv; charset=utf-8",
            headers=headers,
        )
    finally:
        session.close()


@router.get("/exports/{export_id}/download-suggested")
async def download_suggested_export(export_id: int, year: int = 2026):
    factory = get_session_factory()
    session = factory()
    try:
        export = repository.get_export(session, export_id)
        if export is None:
            return Response(status_code=404, content="Not found")
        review = build_export_review(session, export, year)
        rules = load_rules(session)
        accepted = {s.id for s in review.stored + review.suggestions}
        rider_map, team_map = maps_for_accepted(
            review.stored + review.suggestions,
            accepted,
            rules,
        )
        suggested = apply_maps_to_csv(export.csv_text, rider_map, team_map)
        stem = Path(export.filename).stem
        download_name = f"suggested_{stem}.csv"
        headers = {
            "Content-Disposition": f'attachment; filename="{download_name}"',
        }
        return Response(
            content=suggested,
            media_type="text/csv; charset=utf-8",
            headers=headers,
        )
    finally:
        session.close()


@router.get("/exports/{export_id}/review", response_class=HTMLResponse)
async def export_review(request: Request, export_id: int, year: int = 2026, error: str | None = None):
    factory = get_session_factory()
    session = factory()
    try:
        export = session.scalar(
            select(ResultExport)
            .where(ResultExport.id == export_id)
            .options(joinedload(ResultExport.event))
        )
        if export is None:
            return Response(status_code=404, content="Not found")
        review = build_export_review(session, export, year)
        csv_diff = None
        if export.previous_csv_text:
            csv_diff = csv_text_diff(export.previous_csv_text, export.csv_text)
        return templates.TemplateResponse(
            request=request,
            name="admin/results_review.html",
            context={
                "year": year,
                "review": review,
                "export_id": export_id,
                "csv_diff": csv_diff,
                "error": error,
            },
        )
    finally:
        session.close()


def _finish_ingest(
    session,
    export: ResultExport,
    year: int,
    *,
    stored_rider_rules=None,
    stored_team_rules=None,
) -> None:
    repository.mark_export_ingested(session, export)
    refresh_season_from_exports(
        session,
        year,
        stored_rider_rules=stored_rider_rules,
        stored_team_rules=stored_team_rules,
    )


@router.post("/exports/{export_id}/confirm")
async def export_confirm(
    export_id: int,
    year: int = Form(...),
    action: str = Form("confirm"),
    accept: list[str] | None = Form(None),
    file: UploadFile | None = File(None),
    confirm_overwrite: str | None = Form(None),
):
    factory = get_session_factory()
    session = factory()
    try:
        export = repository.get_export(session, export_id)
        if export is None:
            return Response(status_code=404, content="Not found")
        if action == "reupload":
            if not file or not file.filename:
                raise ExportError("Choose a file to re-upload.")
            data = await file.read()
            from app.results.domain.exports import safe_filename
            from app.results.domain.raw_export import file_to_sanitized_csv
            from pathlib import Path
            import tempfile

            tmp = Path(tempfile.mkdtemp()) / safe_filename(file.filename)
            tmp.write_bytes(data)
            csv_text = file_to_sanitized_csv(tmp)
            tmp.unlink(missing_ok=True)
            if not csv_text:
                raise ExportError("File is empty or not a valid CrossMgr export after sanitizing")
            export.csv_text = csv_text

        if export.previous_csv_text and confirm_overwrite != "yes":
            return RedirectResponse(
                url=f"/admin/results/exports/{export_id}/review?year={year}&error="
                "Check the box to confirm overwriting standings for this season.",
                status_code=303,
            )

        review = build_export_review(session, export, year)
        rules = load_rules(session)
        accepted_ids = _parse_id_list(accept)
        new_ids = {s.id for s in review.suggestions}
        ignored_ids = new_ids - accepted_ids
        validate_confirm(export.csv_text, review.suggestions, accepted_ids, ignored_ids)

        rider_map, team_map = maps_for_accepted(
            review.stored + review.suggestions,
            accepted_ids,
            rules,
        )
        export.csv_text = apply_maps_to_csv(export.csv_text, rider_map, team_map)
        upsert_accepted_suggestions(
            session, review.suggestions, accepted_ids, source="admin"
        )
        stored_rider, stored_team = build_stored_maps_for_refresh(
            rules, review.stored, accepted_ids
        )
        _finish_ingest(
            session,
            export,
            year,
            stored_rider_rules=stored_rider,
            stored_team_rules=stored_team,
        )
        session.commit()
    except ConfirmValidationError as exc:
        session.rollback()
        return RedirectResponse(
            url=f"/admin/results/exports/{export_id}/review?year={year}&error={exc.message}",
            status_code=303,
        )
    except (ExportError, IngestError) as exc:
        session.rollback()
        msg = exc.message if hasattr(exc, "message") else str(exc)
        return RedirectResponse(
            url=f"/admin/results/exports/{export_id}/review?year={year}&error={msg}",
            status_code=303,
        )
    except OperationalError:
        session.rollback()
        return RedirectResponse(
            url=f"/admin/results/exports/{export_id}/review?year={year}&error=Database+not+available",
            status_code=303,
        )
    finally:
        session.close()
    return RedirectResponse(
        url=f"/admin/results/?year={year}&msg=ingested",
        status_code=303,
    )


@router.get("/upload", response_class=HTMLResponse)
async def upload_form(
    request: Request,
    year: int = 2026,
    round_number: int = 1,
    error: str | None = None,
    warn_overwrite: int | None = None,
):
    overwrite_export = None
    factory = get_session_factory()
    if warn_overwrite is not None:
        session = factory()
        try:
            overwrite_export = repository.get_export(session, warn_overwrite)
        finally:
            session.close()
    return templates.TemplateResponse(
        request=request,
        name="admin/results_upload.html",
        context={
            "year": year,
            "round_number": round_number,
            "error": error,
            "overwrite_export": overwrite_export,
        },
    )


@router.post("/upload")
async def upload_submit(
    request: Request,
    year: int = Form(...),
    round_number: int = Form(...),
    file: UploadFile = File(...),
    confirm_overwrite: str | None = Form(None),
):
    if not file.filename:
        return templates.TemplateResponse(
            request=request,
            name="admin/results_upload.html",
            context={
                "year": year,
                "round_number": round_number,
                "error": "No file selected",
            },
            status_code=400,
        )
    data = await file.read()
    factory = get_session_factory()
    session = factory()
    try:
        from app.results.domain.exports import safe_filename

        event = repository.find_event(session, year, round_number)
        if event is None:
            raise ExportError(
                f"No event for {year} round {round_number}. Run db-backfill or add the event first."
            )
        name = safe_filename(file.filename)
        existing = session.scalar(
            select(ResultExport).where(
                ResultExport.event_id == event.id,
                ResultExport.filename == name,
            )
        )
        if (
            existing is not None
            and existing.ingest_status == INGEST_STATUS_INGESTED
            and confirm_overwrite != "yes"
        ):
            return templates.TemplateResponse(
                request=request,
                name="admin/results_upload.html",
                context={
                    "year": year,
                    "round_number": round_number,
                    "error": (
                        "This file was already ingested. "
                        "Replace it only if you intend to regenerate standings for the whole season."
                    ),
                    "overwrite_export": existing,
                    "pending_filename": name,
                    "show_overwrite_confirm": True,
                },
                status_code=400,
            )

        export = store_upload(session, year, round_number, file.filename, data)
        repository.mark_export_pending_review(session, export)
        session.commit()
        export_id = export.id
    except ExportError as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="admin/results_upload.html",
            context={
                "year": year,
                "round_number": round_number,
                "error": exc.message,
            },
            status_code=400,
        )
    except OperationalError:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="admin/results_upload.html",
            context={
                "year": year,
                "round_number": round_number,
                "error": "Database not available.",
            },
            status_code=503,
        )
    finally:
        session.close()
    return RedirectResponse(
        url=f"/admin/results/exports/{export_id}/review?year={year}",
        status_code=303,
    )