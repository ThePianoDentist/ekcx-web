from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db import DEFAULT_DB_PATH

PathLike = Union[str, Path]


def build_sqlite_url(db_path: Optional[PathLike] = None) -> str:
    env_override = os.environ.get("EKCX_DB_PATH")
    path = Path(db_path or env_override or DEFAULT_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


def create_engine_for_path(db_path: Optional[PathLike] = None):
    engine = create_engine(
        build_sqlite_url(db_path),
        future=True,
        echo=False,
    )

    if engine.url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    return engine


def create_session_factory(db_path: Optional[PathLike] = None) -> sessionmaker[Session]:
    engine = create_engine_for_path(db_path)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)