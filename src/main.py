"""
LTADE — Laurent Template AI Data Engineering.

Usage:
    uv run python src/main.py generate-data   # Generate synthetic data
    uv run python src/main.py pipeline         # Run Medallion pipeline
    uv run python src/main.py flowcheck        # Check pipeline status
    uv run python src/main.py describe <table> # Describe dataset via AI
"""

import sys

from src.core.harness import ProjectHarness
from src.core.telemetry import setup_observability

setup_observability("ltade")

harness = ProjectHarness("ltade")


def cmd_generate():
    from data.generators.ecommerce import generate_all

    result = generate_all()
    print(f"\nGenerated: {result}")


def cmd_pipeline():
    from src.pipelines.medallion.run import run_medallion

    run_medallion()


def cmd_flowcheck():
    from cli.flowcheck import main as flowcheck_main

    sys.argv = ["flowcheck", "status"]
    flowcheck_main()


def cmd_describe(table: str):
    import asyncio

    from src.agents.analytics_agent import AnalyticsAgent
    from src.schemas.tasks import Task

    async def run():
        agent = AnalyticsAgent()
        await agent.start()
        result = await agent.handle_task(
            Task(
                task_id="describe",
                task_type="describe_dataset",
                agent_type="analytics",
                payload={"table": table, "db_path": "data/silver.duckdb", "layer": "silver"},
            )
        )
        await agent.stop()
        if result.status == "completed":
            print(f"\nDataset: {result.output['table']}")
            print(f"Rows: {result.output['rows']}")
            for col in result.output.get("columns", []):
                print(
                    f"  {col['column']:25s} {col['type']:15s} nulls:{col['nulls']:>5d}  distinct:{col['distinct']}"
                )
            print(f"\nAI Description:\n{result.output.get('description', 'N/A')}")
        else:
            print(f"Error: {result.error}")

    asyncio.run(run())


def cmd_quality(table: str):
    from src.core.data_quality import DataQualityValidator, QualityCheck

    validator = DataQualityValidator("data/silver.duckdb")
    checks = [
        QualityCheck(column="id", rule="not_null"),
        QualityCheck(column="id", rule="unique"),
    ]
    results = validator.check_table(f"silver.{table}", checks)
    print(validator.report(results))
    validator.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    if cmd == "generate-data":
        cmd_generate()
    elif cmd == "pipeline":
        cmd_pipeline()
    elif cmd == "flowcheck":
        cmd_flowcheck()
    elif cmd == "describe" and len(sys.argv) >= 3:
        cmd_describe(sys.argv[2])
    elif cmd == "quality" and len(sys.argv) >= 3:
        cmd_quality(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
