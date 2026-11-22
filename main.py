from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.events.interfaces.web.routes import router as events_router
from app.results.interfaces.admin.routes import router as admin_results_router
from app.site.interfaces.web.routes import router as site_router
from app.standings.interfaces.web.routes import router as standings_router
from app.users.config import get_session_secret
from app.users.interfaces.admin.middleware import AdminAuthMiddleware
from app.users.interfaces.admin.routes import router as admin_auth_router

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(AdminAuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=get_session_secret(),
    same_site="lax",
    https_only=False,
)

app.include_router(site_router)
app.include_router(events_router)
app.include_router(standings_router)
app.include_router(admin_auth_router, prefix="/admin")
app.include_router(admin_results_router, prefix="/admin/results")