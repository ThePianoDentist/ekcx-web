from __future__ import annotations

from urllib.parse import quote

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

ADMIN_SESSION_USER_ID = "admin_user_id"

_PUBLIC_PATHS = frozenset({"/admin/login", "/admin/logout"})


def is_admin_authenticated(request: Request) -> bool:
    return request.session.get(ADMIN_SESSION_USER_ID) is not None


def admin_login_redirect(request: Request) -> RedirectResponse:
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    next_url = quote(path, safe="")
    return RedirectResponse(url=f"/admin/login?next={next_url}", status_code=303)


class AdminAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path.startswith("/admin") and path not in _PUBLIC_PATHS:
            if not is_admin_authenticated(request):
                return admin_login_redirect(request)
        return await call_next(request)