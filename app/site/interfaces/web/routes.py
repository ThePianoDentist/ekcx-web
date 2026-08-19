from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse

from app.web.templates import templates

router = APIRouter()

FAVICON_PATH = "favicon.ico"


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="home.html", context={"selected": "home"}
    )


@router.get("/static/images/ekcx.jpg", include_in_schema=False)
async def favicon():
    return FileResponse(FAVICON_PATH)


@router.get("/rules", response_class=HTMLResponse)
async def rules(request: Request):
    return templates.TemplateResponse(
        request=request, name="rules.html", context={"selected": "standings"}
    )


@router.get("/faq", response_class=HTMLResponse)
async def faq(request: Request):
    return templates.TemplateResponse(
        request=request, name="faq.html", context={"selected": "standings"}
    )


@router.get("/info", response_class=HTMLResponse)
@router.get("/info/{section}", response_class=HTMLResponse)
async def info(request: Request, section: str = "rules"):
    section = section if section in ("rules", "faq") else "rules"
    return templates.TemplateResponse(
        request=request,
        name="info.html",
        context={"selected": "info", "section": section},
    )


@router.get("/media/", response_class=HTMLResponse)
async def media(request: Request):
    return templates.TemplateResponse(
        request=request, name="media.html", context={"selected": "media"}
    )


@router.get("/privacy/", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse(
        request=request, name="privacy.html", context={"selected": "home"}
    )


@router.get("/betteshangerparkchallenges/", response_class=HTMLResponse)
async def cycling_challenges(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="betteshangerparkchallenges.html",
        context={"selected": "cycling"},
    )
