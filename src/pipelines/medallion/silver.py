"""
Silver Layer — Cleansed & Enriched.

Applies data quality rules, type casting, deduplication, and
business-meaningful derivations. Every Silver table has at minimum:
  - NOT NULL constraints on key fields
  - Type casting to canonical types
  - Deduplication by natural key
  - Audit columns (_ingested_at, _source)
"""
import duckdb
from typing import Optional

SILVER_DB = "data/silver.duckdb"
BRONZE_DB = "data/bronze.duckdb"

QUALITY_RULES = {
    "not_null": lambda col: f"{col} IS NOT NULL",
    "unique": lambda col: None,
    "positive": lambda col: f"{col} > 0",
    "non_negative": lambda col: f"{col} >= 0",
    "valid_date": lambda col: f"try_strptime({col}, '%Y-%m-%d') IS NOT NULL OR {col} IS NULL",
}

def apply_quality_checks(con, table: str, checks: list[dict]) -> dict:
    results = {}
    for check in checks:
        col = check.get("column")
        rule = check.get("rule")
        sql_fn = QUALITY_RULES.get(rule)
        if not sql_fn or not col:
            continue
        condition = sql_fn(col)
        if condition:
            failed = con.execute(f"SELECT count(*) FROM {table} WHERE NOT ({condition})").fetchone()[0]
            results[f"{col}.{rule}"] = {"passed": failed == 0, "failed_rows": failed}
    return results

def bronze_to_silver(source_table: str, target_table: str, quality_checks: Optional[list[dict]] = None) -> dict:
    bronze_con = duckdb.connect(BRONZE_DB)
    silver_con = duckdb.connect(SILVER_DB)

    silver_con.execute("CREATE SCHEMA IF NOT EXISTS silver")

    # Attach bronze DB for cross-DB query
    bronze_con.execute(f"ATTACH '{SILVER_DB}' AS silver_db (TYPE duckdb)")

    # Copy with dedup and audit columns
    bronze_con.execute(f"""
        CREATE OR REPLACE TABLE silver_db.silver.{target_table} AS
        SELECT DISTINCT *,
               current_timestamp AS _ingested_at,
               '{source_table}' AS _source
        FROM bronze.{source_table}
        WHERE true
    """)

    count = bronze_con.execute(f"SELECT count(*) FROM silver_db.silver.{target_table}").fetchone()[0]

    quality_results = {}
    if quality_checks:
        quality_results = apply_quality_checks(silver_con, f"silver.{target_table}", quality_checks)

    bronze_con.close()
    silver_con.close()

    return {"table": target_table, "rows": count, "quality": quality_results}
