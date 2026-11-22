from __future__ import annotations

from fastapi import APIRouter, Form
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from app.db.session import get_session_factory
from app.users.domain.auth import authenticate, normalize_email
from app.users.interfaces.admin.middleware import ADMIN_SESSION_USER_ID
from app.web.templates import templates

router = APIRouter(tags=["admin-auth"])

_DEFAULT_AFTER_LOGIN = "/admin/results/"


def _safe_next_url(next_param: str | None) -> str:
    if not next_param or not next_param.startswith("/admin"):
        return _DEFAULT_AFTER_LOGIN
    return next_param


@router.get("/login", response_class=HTMLResponse)
async def login_form(
    request: Request,
    next: str | None = None,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={
            "error": error,
            "next_url": _safe_next_url(next),
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/admin/results/"),
):
    factory = get_session_factory()
    session = factory()
    try:
        user = authenticate(session, email, password)
    finally:
        session.close()
    next_url = _safe_next_url(next)
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="admin/login.html",
            context={
                "error": "Invalid email or password",
                "next_url": next_url,
                "email": normalize_email(email),
            },
            status_code=401,
        )
    request.session[ADMIN_SESSION_USER_ID] = user.id
    request.session["admin_email"] = user.email
    return RedirectResponse(url=next_url, status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)