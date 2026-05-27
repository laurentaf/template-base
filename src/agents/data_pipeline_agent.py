import asyncio

from src.agents.base import BaseAgent
from src.core.data_quality import DataQualityValidator, QualityCheck
from src.pipelines.medallion import bronze, gold, silver
from src.schemas.messages import AgentMessage
from src.schemas.tasks import Task, TaskResult
from src.tools.database import (
    get_duckdb_connection,
    get_postgres_engine,
    safe_column,
    safe_table,
)


class DataPipelineAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "data-pipeline",
            [
                "etl",
                "elt",
                "data_ingestion",
                "data_transformation",
                "duckdb",
                "postgres",
                "sql",
                "data_quality",
            ],
        )

    async def handle_task(self, task: Task) -> TaskResult:
        ttype = task.task_type
        payload = task.payload

        if ttype == "run_query":
            return await self._run_query(payload, task.task_id)
        if ttype == "ingest_file":
            return await self._ingest_file(payload, task.task_id)
        if ttype == "transform":
            return await self._transform(payload, task.task_id)
        if ttype == "validate":
            return await self._validate(payload, task.task_id)
        if ttype == "validate_all":
            return await self._validate_comprehensive(payload, task.task_id)
        if ttype == "export":
            return await self._export(payload, task.task_id)
        if ttype == "run_medallion":
            return await self._run_medallion(payload, task.task_id)
        if ttype == "bronze_ingest":
            return await self._bronze_ingest(payload, task.task_id)
        if ttype == "silver_transform":
            return await self._silver_transform(payload, task.task_id)
        if ttype == "gold_aggregate":
            return await self._gold_aggregate(payload, task.task_id)
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown: {ttype}")

    async def _run_query(self, payload: dict, task_id: str) -> TaskResult:
        query = payload.get("query", "")
        source = payload.get("source", "duckdb")
        db_path = payload.get("db_path", ":memory:")
        try:
            if source == "duckdb":
                con = get_duckdb_connection(db_path)
                result = con.execute(query).fetchdf()
                con.close()
            else:
                engine = get_postgres_engine()
                result = engine.execute(query).fetchall()
            return TaskResult(
                task_id=task_id,
                status="completed",
                output={
                    "rows": len(result),
                    "columns": list(result.columns) if hasattr(result, "columns") else [],
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _ingest_file(self, payload: dict, task_id: str) -> TaskResult:
        path = payload.get("path", "")
        table = payload.get("table", "ingested_data")
        db_path = payload.get("db_path", ":memory:")
        try:
            con = get_duckdb_connection(db_path)
            qtable = safe_table(table)
            con.execute(f"CREATE TABLE {qtable} AS SELECT * FROM read_csv_auto(?)", [path])
            count = con.execute(f"SELECT count(*) FROM {qtable}").fetchone()[0]
            con.close()
            return TaskResult(
                task_id=task_id,
                status="completed",
                output={
                    "table": table,
                    "rows_ingested": count,
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _transform(self, payload: dict, task_id: str) -> TaskResult:
        query = payload.get("query", "")
        output_table = payload.get("output_table", "transformed")
        db_path = payload.get("db_path", ":memory:")
        try:
            con = get_duckdb_connection(db_path)
            qtable = safe_table(output_table)
            con.execute(f"CREATE OR REPLACE TABLE {qtable} AS ({query})")
            count = con.execute(f"SELECT count(*) FROM {qtable}").fetchone()[0]
            con.close()
            return TaskResult(
                task_id=task_id,
                status="completed",
                output={
                    "output_table": output_table,
                    "rows": count,
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _validate(self, payload: dict, task_id: str) -> TaskResult:
        table = payload.get("table", "")
        checks = payload.get("checks", [])
        db_path = payload.get("db_path", ":memory:")
        results = []
        try:
            con = get_duckdb_connection(db_path)
            tref = safe_table(table)
            for check in checks:
                check_type = check.get("type")
                column = check.get("column")
                qcol = safe_column(column)
                if check_type == "not_null":
                    nulls = con.execute(
                        f"SELECT count(*) FROM {tref} WHERE {qcol} IS NULL"
                    ).fetchone()[0]
                    results.append(
                        {"check": f"{column} NOT NULL", "passed": nulls == 0, "null_count": nulls}
                    )
                elif check_type == "unique":
                    total = con.execute(f"SELECT count(*) FROM {tref}").fetchone()[0]
                    unique = con.execute(f"SELECT count(DISTINCT {qcol}) FROM {tref}").fetchone()[0]
                    results.append(
                        {
                            "check": f"{column} UNIQUE",
                            "passed": total == unique,
                            "total": total,
                            "unique": unique,
                        }
                    )
            con.close()
            failed = [r for r in results if not r["passed"]]
            return TaskResult(
                task_id=task_id,
                status="completed" if not failed else "failed",
                output={
                    "table": table,
                    "checks": results,
                    "passed": len(results) - len(failed),
                    "failed": len(failed),
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _export(self, payload: dict, task_id: str) -> TaskResult:
        table = payload.get("table", "")
        fmt = payload.get("format", "parquet")
        output_path = payload.get("output_path", f"exports/{table}.{fmt}")
        db_path = payload.get("db_path", ":memory:")
        try:
            con = get_duckdb_connection(db_path)
            qtable = safe_table(table)
            if fmt == "parquet":
                con.execute(f"COPY {qtable} TO ? (FORMAT PARQUET)", [output_path])
            else:
                con.execute(f"COPY {qtable} TO ? (FORMAT CSV, HEADER)", [output_path])
            con.close()
            return TaskResult(task_id=task_id, status="completed", output={"path": output_path})
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _validate_comprehensive(self, payload: dict, task_id: str) -> TaskResult:
        table = payload.get("table", "")
        db_path = payload.get("db_path", ":memory:")
        columns = payload.get("columns", [])
        rules = payload.get("rules", ["not_null"])
        try:
            validator = DataQualityValidator(db_path)
            checks = []
            for col in columns:
                for rule in rules:
                    checks.append(QualityCheck(column=col, rule=rule))
            results = validator.check_table(table, checks)
            report = validator.report(results)
            validator.close()
            return TaskResult(
                task_id=task_id,
                status="completed",
                output={
                    "table": table,
                    "checks": len(results),
                    "passed": sum(1 for r in results if r.passed),
                    "failed": sum(1 for r in results if not r.passed),
                    "report": report,
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _run_medallion(self, payload: dict, task_id: str) -> TaskResult:
        try:
            bronze_r = bronze.ingest_all()
            tables = bronze.list_bronze_tables()
            silver_r = {}
            for t in tables:
                silver_r[t] = silver.bronze_to_silver(t, t)
            gold_r = gold.build_analytics_views()
            return TaskResult(
                task_id=task_id,
                status="completed",
                output={
                    "bronze": bronze_r,
                    "silver": {k: v["rows"] for k, v in silver_r.items()},
                    "gold": gold_r,
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _bronze_ingest(self, payload: dict, task_id: str) -> TaskResult:
        file_path = payload.get("file_path", "")
        table = payload.get("table", "")
        try:
            if file_path.endswith(".csv"):
                count = bronze.ingest_csv(table, file_path)
            else:
                count = bronze.ingest_json(table, file_path)
            return TaskResult(
                task_id=task_id, status="completed", output={"table": table, "rows": count}
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _silver_transform(self, payload: dict, task_id: str) -> TaskResult:
        source = payload.get("source", "")
        target = payload.get("target", source)
        checks = payload.get("checks")
        try:
            result = silver.bronze_to_silver(source, target, quality_checks=checks)
            return TaskResult(task_id=task_id, status="completed", output=result)
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _gold_aggregate(self, payload: dict, task_id: str) -> TaskResult:
        sql = payload.get("sql", "")
        view = payload.get("view", "analytics_view")
        try:
            result = gold.create_aggregation(sql, view)
            return TaskResult(task_id=task_id, status="completed", output=result)
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def on_message(self, msg: AgentMessage):
        if msg.topic == "workflow.assigned":
            self.log(f"Assigned to workflow: {msg.payload.get('workflow_id')}")


async def main():
    agent = DataPipelineAgent()
    await agent.start()
    agent.log("Data Pipeline Agent ready.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
