"""
Gold Layer — Business Analytics.

Materialized views and aggregations for reporting, dashboards,
and ML feature engineering. Gold tables are analytics-ready.
"""
import duckdb

GOLD_DB = "data/gold.duckdb"
SILVER_DB = "data/silver.duckdb"

def create_aggregation(sql: str, view_name: str) -> dict:
    con = duckdb.connect(GOLD_DB)
    con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    con.execute(f"ATTACH '{SILVER_DB}' AS silver_db (TYPE duckdb)")
    con.execute(f"CREATE OR REPLACE VIEW gold.{view_name} AS {sql}")
    count = con.execute(f"SELECT count(*) FROM gold.{view_name}").fetchone()[0]
    con.close()
    return {"view": view_name, "rows": count}

def build_analytics_views() -> list[dict]:
    results = []
    results.append(create_aggregation(
        "SELECT * FROM silver_db.silver.orders", "orders_analytics"
    ))
    return results
