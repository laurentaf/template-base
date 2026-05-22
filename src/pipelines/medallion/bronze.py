"""
Bronze Layer — Raw Ingestion.

Ingests raw data from source files (CSV, JSON, Parquet) into DuckDB
with minimal transformation. Preserves original data for re-processing.
"""
import duckdb
from pathlib import Path
from typing import Optional

BRONZE_DB = "data/bronze.duckdb"

def ingest_csv(table_name: str, file_path: str, db_path: str = BRONZE_DB) -> int:
    con = duckdb.connect(db_path)
    con.execute(f"CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute(f"CREATE OR REPLACE TABLE bronze.{table_name} AS SELECT * FROM read_csv_auto('{file_path}')")
    count = con.execute(f"SELECT count(*) FROM bronze.{table_name}").fetchone()[0]
    con.close()
    return count

def ingest_json(table_name: str, file_path: str, db_path: str = BRONZE_DB) -> int:
    con = duckdb.connect(db_path)
    con.execute(f"CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute(f"CREATE OR REPLACE TABLE bronze.{table_name} AS SELECT * FROM read_json_auto('{file_path}')")
    count = con.execute(f"SELECT count(*) FROM bronze.{table_name}").fetchone()[0]
    con.close()
    return count

def list_bronze_tables(db_path: str = BRONZE_DB) -> list[str]:
    con = duckdb.connect(db_path)
    tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'bronze'").fetchall()
    con.close()
    return [t[0] for t in tables]

def ingest_all(data_dir: str = "data/sample", db_path: str = BRONZE_DB) -> dict[str, int]:
    results = {}
    for f in Path(data_dir).glob("*"):
        if f.suffix == ".csv":
            results[f.stem] = ingest_csv(f.stem, str(f), db_path)
        elif f.suffix == ".json":
            results[f.stem] = ingest_json(f.stem, str(f), db_path)
    return results
