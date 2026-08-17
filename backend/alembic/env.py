"""Alembic environment.

The database URL comes from DATABASE_DIRECT_URL in the environment, never from
alembic.ini, so no credential is ever committed. Migrations use the DIRECT
(non-pooled) connection because DDL does not work reliably through a
transaction pooler.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.models import Base  # imports every model, populating Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    settings = get_settings()
    url = settings.database_direct_url or settings.database_url
    if not url:
        raise RuntimeError(
            "No database URL configured. Set DATABASE_DIRECT_URL in .env "
            "(Supabase dashboard -> Project Settings -> Database -> "
            "Connection string -> Direct connection)."
        )
    # Alembic runs synchronously; strip any async driver suffix.
    return url.replace("+asyncpg", "+psycopg")


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
