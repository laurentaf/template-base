"""
Run the full Medallion pipeline: Bronze -> Silver -> Gold.
Uses Prefect for orchestration with retry, logging, and observability.

Usage:
    uv run python -m src.pipelines.medallion.run
"""

from prefect import flow, task

from src.core.telemetry import setup_observability
from src.pipelines.medallion import bronze, gold, silver


@task(retries=2, retry_delay_seconds=5, log_prints=True)
def ingest_bronze(data_dir: str) -> dict:
    print(f"[Bronze] Ingesting from {data_dir}...")
    results = bronze.ingest_all(data_dir)
    for table, count in results.items():
        print(f"  {table}: {count} rows")
    return results


@task(retries=1, retry_delay_seconds=3, log_prints=True)
def transform_silver(tables: list[str]) -> dict:
    print("[Silver] Applying quality checks and dedup...")
    results = {}
    for table in tables:
        result = silver.bronze_to_silver(
            table,
            table,
            quality_checks=[
                {"column": "id", "rule": "not_null"},
            ],
        )
        results[table] = result["rows"]
        for check, status in result.get("quality", {}).items():
            marker = "PASS" if status["passed"] else "FAIL"
            print(f"  {table}.{check}: {marker} (failed: {status['failed_rows']})")
    return results


@task(log_prints=True)
def build_gold() -> list[dict]:
    print("[Gold] Building analytics views...")
    results = gold.build_analytics_views()
    for r in results:
        print(f"  {r['view']}: {r['rows']} rows")
    return results


@flow(name="medallion-pipeline", log_prints=True)
def run_medallion(data_dir: str = "data/sample"):
    setup_observability("medallion-pipeline")
    print("=" * 50)
    print("Medallion Pipeline: Bronze -> Silver -> Gold")
    print("=" * 50)

    ingest_result = ingest_bronze(data_dir)
    tables = list(ingest_result.keys())
    if not tables:
        print("No data found to process.")
        return

    silver_result = transform_silver(tables)
    gold_result = build_gold()

    print("\nPipeline complete")
    print(f"  Bronze: data/bronze.duckdb — {len(ingest_result)} tables")
    print(f"  Silver: data/silver.duckdb — {len(silver_result)} tables")
    print(f"  Gold:   data/gold.duckdb   — {len(gold_result)} views")


def run():
    run_medallion()


if __name__ == "__main__":
    run()
