import duckdb
from sqlalchemy import create_engine

from src.core.config import settings


def get_duckdb_connection(db_path: str = ":memory:"):
    return duckdb.connect(db_path)


def get_postgres_engine():
    return create_engine(settings.DATABASE_URL)
