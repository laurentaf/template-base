"""
Silver Layer — Cleansed & Enriched.
"""

import duckdb

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
            failed = con.execute(
                f"SELECT count(*) FROM {table} WHERE NOT ({condition})"
            ).fetchone()[0]
            results[f"{col}.{rule}"] = {"passed": failed == 0, "failed_rows": failed}
    return results


def bronze_to_silver(
    source_table: str,
    target_table: str,
    quality_checks: list[dict] | None = None,
    db_path: str | None = None,
    silver_path: str | None = None,
) -> dict:
    bronze_db = db_path or BRONZE_DB
    silver_db = silver_path or SILVER_DB

    bronze_con = duckdb.connect(bronze_db)
    prefix = bronze_con.execute("SELECT current_database()").fetchone()[0]
    df = bronze_con.execute(f"SELECT * FROM {prefix}.bronze.{source_table}").fetchdf()
    bronze_con.close()

    silver_con = duckdb.connect(silver_db)
    silver_con.execute("CREATE SCHEMA IF NOT EXISTS silver")
    silver_con.execute(f"DROP TABLE IF EXISTS silver.{target_table}")

    if len(df) > 0:
        dedup_cols = [c for c in df.columns if c not in ("_ingested_at", "_source")]
        df = df.drop_duplicates(subset=dedup_cols) if dedup_cols else df.drop_duplicates()
        ts = duckdb.execute("SELECT current_timestamp").fetchone()[0]
        df["_ingested_at"] = ts
        df["_source"] = source_table
        silver_con.execute(f"CREATE TABLE silver.{target_table} AS SELECT * FROM df")
    else:
        silver_con.execute(f"CREATE TABLE silver.{target_table} AS SELECT NULL LIMIT 0")

    count = silver_con.execute(f"SELECT count(*) FROM silver.{target_table}").fetchone()[0]

    quality_results = {}
    if quality_checks:
        quality_results = apply_quality_checks(silver_con, f"silver.{target_table}", quality_checks)

    silver_con.close()
    return {"table": target_table, "rows": count, "quality": quality_results}
