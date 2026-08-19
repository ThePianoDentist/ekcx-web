from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.events.interfaces.web.routes import router as events_router
from app.site.interfaces.web.routes import router as site_router
from app.standings.interfaces.web.routes import router as standings_router

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(site_router)
app.include_router(events_router)
app.include_router(standings_router)
