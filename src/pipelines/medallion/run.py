"""
Run the full Medallion pipeline: Bronze → Silver → Gold.

Usage:
    uv run python -m src.pipelines.medallion.run
"""
from src.pipelines.medallion import bronze, silver, gold
from src.core.telemetry import setup_observability

def run():
    setup_observability("medallion-pipeline")

    print("=" * 50)
    print("Medallion Pipeline: Bronze → Silver → Gold")
    print("=" * 50)

    # Phase 1: Bronze — Raw ingestion
    print("\n[Bronze] Ingesting raw data...")
    bronze_results = bronze.ingest_all()
    for table, count in bronze_results.items():
        print(f"  {table}: {count} rows")
    tables = bronze.list_bronze_tables()

    # Phase 2: Silver — Cleansed & enriched
    print("\n[Silver] Applying quality checks...")
    for table in tables:
        result = silver.bronze_to_silver(table, table, quality_checks=[
            {"column": "id", "rule": "not_null"},
        ])
        print(f"  {table}: {result['rows']} rows")
        for check, status in result.get("quality", {}).items():
            marker = "✅" if status["passed"] else "❌"
            print(f"    {marker} {check} (failed: {status['failed_rows']})")

    # Phase 3: Gold — Business analytics
    print("\n[Gold] Building analytics views...")
    gold_results = gold.build_analytics_views()
    for r in gold_results:
        print(f"  {r['view']}: {r['rows']} rows")

    print("\n✅ Pipeline complete")
    print(f"  Bronze: data/bronze.duckdb")
    print(f"  Silver: data/silver.duckdb")
    print(f"  Gold:   data/gold.duckdb")

if __name__ == "__main__":
    run()
