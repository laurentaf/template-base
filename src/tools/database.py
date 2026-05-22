import duckdb
from qdrant_client import QdrantClient
from sqlalchemy import create_engine

try:
    from .config import settings
except ImportError:
    import config as settings


def get_duckdb_connection(db_path: str = ":memory:"):
    """Returns a DuckDB connection (defaults to in-memory)."""
    return duckdb.connect(db_path)


def get_postgres_engine():
    """Returns a SQLAlchemy engine for the Postgres instance."""
    return create_engine(settings.DATABASE_URL)


def get_qdrant_client():
    """Returns a Qdrant client."""
    return QdrantClient(url=settings.QDRANT_URL)


def run_query_as_df(query: str):
    """Utility to run a SQL query directly into a Pandas/DuckDB DataFrame."""
    with get_duckdb_connection() as con:
        return con.query(query).df()
