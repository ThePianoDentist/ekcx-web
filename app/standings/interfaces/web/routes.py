from fastapi import APIRouter, Query
from sqlalchemy.exc import OperationalError
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from app.db.session import get_session_factory
from app.standings.config import (
    CURRENT_DB_STANDINGS_FROM_YEAR,
    resolve_standings_source,
    standings_nav_query,
    uses_database,
)
from app.standings.domain.render import render_standings
from app.web.templates import templates

router = APIRouter()


@router.get("/standings/{year}/{category}", response_class=HTMLResponse)
async def standings(
    request: Request,
    category: str,
    year: int,
    source: str | None = Query(default=None, pattern="^(static|db)$"),
):
    year = year or 2026
    resolved = resolve_standings_source(year, source)
    use_db = uses_database(year, resolved)
    if year >= CURRENT_DB_STANDINGS_FROM_YEAR and category == "mens":
        url = f"/standings/{year}/v40"
        nav_q = standings_nav_query(year, resolved)
        if nav_q:
            url += nav_q
        return RedirectResponse(url=url, status_code=302)
    standings_html = _from_database(year, category) if use_db else None
    nav_q = standings_nav_query(year, resolved)
    return templates.TemplateResponse(
        request=request,
        name="standings.html",
        context={
            "category": category,
            "year": year,
            "selected": "standings",
            "standings_html": standings_html,
            "nav_q": nav_q,
        },
    )


def _from_database(year: int, category: str) -> str:
    factory = get_session_factory()
    session = factory()
    try:
        return render_standings(session, year, category)
    except OperationalError:
        return "<p>No standings database for this season yet.</p>"
    finally:
        session.close()