from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base
from app.db.session import build_sqlite_url
from app.events.data import models as events_models  # noqa: F401
from app.participants.data import models as participants_models  # noqa: F401
from app.results.data import models as results_models  # noqa: F401
from app.standings.data import models as standings_models  # noqa: F401
from app.users.data import models as users_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    if os.environ.get("EKCX_DB_PATH"):
        return build_sqlite_url()
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url and ini_url.startswith("sqlite:///") and not ini_url.startswith("sqlite:////"):
        path = Path(ini_url.removeprefix("sqlite:///"))
        if not path.is_absolute():
            root = Path(__file__).resolve().parents[1]
            path = root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"
    return ini_url or build_sqlite_url()


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()