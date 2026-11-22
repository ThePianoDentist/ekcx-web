from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.db import session as db_session
from app.users.data import repository
from app.users.domain.auth import hash_password, normalize_email

ADMIN_PASSWORD = "test-admin-password"
ADMIN_EMAIL = "admin@ekcx.test"


@pytest.fixture
def auth_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Setup:
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("EKCX_DB_PATH", str(db_path))
    monkeypatch.setenv("EKCX_SESSION_SECRET", "test-session-secret-for-pytest-only")
    db_session._session_factory = None

    root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(alembic_cfg, "head")

    factory = db_session.create_session_factory(db_path)
    with factory() as session:
        repository.create_user(
            session,
            normalize_email(ADMIN_EMAIL),
            hash_password(ADMIN_PASSWORD),
        )
        session.commit()

    import main

    importlib.reload(main)
    yield
    db_session._session_factory = None


@pytest.fixture
def client(auth_env):
    # Setup:
    import main

    return TestClient(main.app)


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD) -> None:
  # Setup:
    response = client.post(
        "/admin/login",
        data={"email": email, "password": password, "next": "/admin/results/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_unauthenticated_admin_redirects_to_login(client: TestClient):
    # Run:
    response = client.get("/admin/", follow_redirects=False)
    # Check:
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/login?next=")
    response = client.get("/admin/results/", follow_redirects=False)
    # Check:
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/login?next=")


def test_login_then_access_admin(client: TestClient):
    # Run:
    _login(client)
    response = client.get("/admin/results/")
    # Check:
    assert response.status_code == 200
    assert "Result exports" in response.text


def test_wrong_password_shows_error(client: TestClient):
    # Run:
    response = client.post(
        "/admin/login",
        data={
            "email": ADMIN_EMAIL,
            "password": "wrong",
            "next": "/admin/results/",
        },
        follow_redirects=False,
    )
    blocked = client.get("/admin/results/", follow_redirects=False)
    # Check:
    assert response.status_code == 401
    assert "Invalid email or password" in response.text
    assert blocked.status_code == 303


def test_admin_homepage(client: TestClient):
    # Run:
    _login(client)
    response = client.get("/admin/")
    # Check:
    assert response.status_code == 200
    assert "Upload results" in response.text
    assert "/admin/results/upload" in response.text


def test_logout_clears_session(client: TestClient):
    # Setup:
    _login(client)
    # Run:
    response = client.post("/admin/logout", follow_redirects=False)
    blocked = client.get("/admin/results/", follow_redirects=False)
    # Check:
    assert response.status_code == 303
    assert blocked.status_code == 303