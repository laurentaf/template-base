import duckdb

from src.core.config import settings


def get_duckdb_connection(db_path: str = ":memory:"):
    return duckdb.connect(db_path)


def get_postgres_engine():
    try:
        from sqlalchemy import create_engine

        engine = create_engine(settings.DATABASE_URL)
        engine.connect().close()
        return engine
    except Exception:
        con = duckdb.connect()
        return _DuckFallbackEngine(con)


class _DuckFallbackEngine:
    def __init__(self, con):
        self._con = con

    def execute(self, sql, params=None):
        if params:
            return self._con.execute(sql, params)
        return self._con.execute(sql)
