from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from sqlalchemy.exc import OperationalError
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from app.db.session import get_session_factory
from app.results.data import repository
from app.results.domain.exports import ExportError, list_exports_for_season, store_upload
from app.web.templates import templates

router = APIRouter(tags=["admin-results"])


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


@router.get("/upload", response_class=HTMLResponse)
async def upload_form(
    request: Request,
    year: int = 2026,
    round_number: int = 1,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="admin/results_upload.html",
        context={
            "year": year,
            "round_number": round_number,
            "error": error,
        },
    )


@router.post("/upload")
async def upload_submit(
    request: Request,
    year: int = Form(...),
    round_number: int = Form(...),
    file: UploadFile = File(...),
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
        store_upload(session, year, round_number, file.filename, data)
        session.commit()
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
        url=f"/admin/results/?year={year}&msg=uploaded",
        status_code=303,
    )