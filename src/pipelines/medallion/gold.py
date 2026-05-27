"""
Gold Layer — Business Analytics.

Materialized views and aggregations for reporting, dashboards,
and ML feature engineering. Gold tables are analytics-ready.
Dynamically discovers silver tables from DuckDB catalog.
"""

import duckdb

from src.tools.database import safe_layer, safe_table

GOLD_DB = "data/gold.duckdb"
SILVER_DB = "data/silver.duckdb"


def discover_silver_tables(silver_db: str = SILVER_DB) -> list[tuple[str, str]]:
    """Discover (schema, table) pairs in the silver database."""
    con = duckdb.connect(silver_db, read_only=True)
    try:
        rows = con.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('main', 'information_schema', 'pg_catalog')"
        ).fetchall()
        return [(schema, name) for schema, name in rows]
    except Exception:
        return []
    finally:
        con.close()


def create_aggregation(sql: str, view_name: str) -> dict:
    gold_con = duckdb.connect(GOLD_DB)
    gold_con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    qview = safe_table(view_name)
    gold_con.execute(f"DROP VIEW IF EXISTS gold.{qview}")
    gold_con.execute(f"CREATE VIEW gold.{qview} AS ({sql})")
    count = gold_con.execute(f"SELECT count(*) FROM gold.{qview}").fetchone()[0]
    gold_con.close()
    return {"view": view_name, "rows": count}


def build_analytics_views() -> list[dict]:
    results = []
    silver_tables = discover_silver_tables()
    if not silver_tables:
        results.append(create_aggregation("SELECT 1 AS placeholder", "placeholder"))
        return results

    for schema, table in silver_tables:
        qref = f"{safe_layer(schema)}.{safe_table(table)}"
        view_name = f"{table}_analytics"
        try:
            results.append(create_aggregation(f"SELECT * FROM {qref}", view_name))
        except Exception:
            pass
    return results
