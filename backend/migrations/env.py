"""Alembic environment. Migrations run as the database OWNER role (RLS does not apply to it)."""
from alembic import context
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.models import Base

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # PostGIS / tiger tables live in the same database; never touch them.
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


def run_migrations_online() -> None:
    engine = create_engine(get_settings().database_owner_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
