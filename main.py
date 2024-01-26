from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse, FileResponse
from starlette.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/")
async def main_route(request: Request):
    return templates.TemplateResponse(
        request=request, name="home.html", context={"selected": "home"}
    )

favicon_path = 'favicon.ico'


@app.get('/static/images/ekcx.jpg', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


@app.get("/standings/{category}", response_class=HTMLResponse)
async def standings(request: Request, category: str):
    return templates.TemplateResponse(
        request=request, name="standings.html", context={"category": category, "selected": "standings"}
    )

@app.get("/media/", response_class=HTMLResponse)
async def media(request: Request):
    return templates.TemplateResponse(
        request=request, name="media.html", context={"selected": "media"}
    )

@app.get("/forum/", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse(
        request=request, name="forum.html", context={"selected": "forum"}
    )

@app.get("/privacy/", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse(
        request=request, name="privacy.html", context={"selected": "home"}
    )
