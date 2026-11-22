from fastapi import APIRouter, Query
from sqlalchemy.exc import OperationalError
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from app.db.session import get_session_factory
from app.standings.domain.render import render_standings
from app.web.templates import templates

router = APIRouter()

# From 2026, seniors start in the Masters 40 race, so that page is the joined classification.
JOINED_OPEN_FROM_YEAR = 2026


def shows_database(year: int, source: str) -> bool:
    """2026 can be read from SQLite. Older seasons stay on the static pages."""
    return year >= JOINED_OPEN_FROM_YEAR and source == "db"


@router.get("/standings/{year}/{category}", response_class=HTMLResponse)
async def standings(
    request: Request,
    category: str,
    year: int,
    source: str = Query(default="static"),
):
    year = year or 2026
    use_db = shows_database(year, source)
    if year >= JOINED_OPEN_FROM_YEAR and category == "mens":
        url = f"/standings/{year}/v40"
        if use_db:
            url += "?source=db"
        return RedirectResponse(url=url, status_code=302)
    standings_html = _from_database(year, category) if use_db else None
    return templates.TemplateResponse(
        request=request,
        name="standings.html",
        context={
            "category": category,
            "year": year,
            "selected": "standings",
            "source": "db" if use_db else "static",
            "standings_html": standings_html,
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
