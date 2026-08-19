from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import HTMLResponse

from app.web.templates import templates

router = APIRouter()


@router.get("/standings/{year}/{category}", response_class=HTMLResponse)
async def standings(request: Request, category: str, year: int):
    year = year or 2025
    return templates.TemplateResponse(
        request=request,
        name="standings.html",
        context={"category": category, "year": year, "selected": "standings"},
    )
