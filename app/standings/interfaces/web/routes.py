from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from app.web.templates import templates

router = APIRouter()

# From 2026, seniors start in the Masters 40 race, so that page is the joined classification.
JOINED_OPEN_FROM_YEAR = 2026


@router.get("/standings/{year}/{category}", response_class=HTMLResponse)
async def standings(request: Request, category: str, year: int):
    year = year or 2026
    if year >= JOINED_OPEN_FROM_YEAR and category == "mens":
        return RedirectResponse(url=f"/standings/{year}/v40", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="standings.html",
        context={"category": category, "year": year, "selected": "standings"},
    )
