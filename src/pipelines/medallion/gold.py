"""
Gold Layer — Business Analytics.

Materialized views and aggregations for reporting, dashboards,
and ML feature engineering. Gold tables are analytics-ready.
"""

import duckdb

GOLD_DB = "data/gold.duckdb"
SILVER_DB = "data/silver.duckdb"


def create_aggregation(sql: str, view_name: str) -> dict:
    gold_con = duckdb.connect(GOLD_DB)
    gold_con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    gold_con.execute(f"DROP VIEW IF EXISTS gold.{view_name}")
    gold_con.execute(
        f"CREATE VIEW gold.{view_name} AS ({sql})"
    )
    count = gold_con.execute(f"SELECT count(*) FROM gold.{view_name}").fetchone()[0]
    gold_con.close()
    return {"view": view_name, "rows": count}


def build_analytics_views() -> list[dict]:
    results = []
    results.append(create_aggregation("SELECT * FROM silver.orders", "orders_analytics"))
    return results
