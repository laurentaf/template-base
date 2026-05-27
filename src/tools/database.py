import re

import duckdb

from src.core.config import settings

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_ALLOWED_LAYERS = {"bronze", "silver", "gold", "main", "information_schema"}


def quote_identifier(name: str) -> str:
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'


def safe_layer(layer: str) -> str:
    if layer not in _ALLOWED_LAYERS:
        raise ValueError(f"Unknown schema/layer: {layer!r}")
    return quote_identifier(layer)


def safe_table(table: str) -> str:
    return quote_identifier(table)


def safe_column(col: str) -> str:
    return quote_identifier(col)


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
