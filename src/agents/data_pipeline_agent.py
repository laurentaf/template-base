import duckdb
from src.agents.base import BaseAgent
from src.schemas.tasks import Task, TaskResult
from src.schemas.messages import AgentMessage
from src.tools.database import get_duckdb_connection, get_postgres_engine

class DataPipelineAgent(BaseAgent):
    def __init__(self):
        super().__init__("data-pipeline", [
            "etl", "elt", "data_ingestion", "data_transformation",
            "duckdb", "postgres", "sql", "data_quality"
        ])

    async def handle_task(self, task: Task) -> TaskResult:
        ttype = task.task_type
        payload = task.payload

        if ttype == "run_query":
            return await self._run_query(payload)
        if ttype == "ingest_file":
            return await self._ingest_file(payload)
        if ttype == "transform":
            return await self._transform(payload)
        if ttype == "validate":
            return await self._validate(payload)
        if ttype == "export":
            return await self._export(payload)
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown: {ttype}")

    async def _run_query(self, payload: dict) -> TaskResult:
        query = payload.get("query", "")
        source = payload.get("source", "duckdb")
        try:
            if source == "duckdb":
                con = get_duckdb_connection()
                result = con.execute(query).fetchdf()
            else:
                engine = get_postgres_engine()
                result = engine.execute(query).fetchall()
            return TaskResult(task_id=task.task_id, status="completed", output={
                "rows": len(result), "columns": list(result.columns) if hasattr(result, "columns") else []
            })
        except Exception as e:
            return TaskResult(task_id=task.task_id, status="failed", error=str(e))

    async def _ingest_file(self, payload: dict) -> TaskResult:
        path = payload.get("path", "")
        table = payload.get("table", "ingested_data")
        try:
            con = get_duckdb_connection()
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto('{path}')")
            count = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            return TaskResult(task_id=task.task_id, status="completed", output={
                "table": table, "rows_ingested": count
            })
        except Exception as e:
            return TaskResult(task_id=task.task_id, status="failed", error=str(e))

    async def _transform(self, payload: dict) -> TaskResult:
        query = payload.get("query", "")
        output_table = payload.get("output_table", "transformed")
        try:
            con = get_duckdb_connection()
            con.execute(f"CREATE OR REPLACE TABLE {output_table} AS ({query})")
            count = con.execute(f"SELECT count(*) FROM {output_table}").fetchone()[0]
            return TaskResult(task_id=task.task_id, status="completed", output={
                "output_table": output_table, "rows": count
            })
        except Exception as e:
            return TaskResult(task_id=task.task_id, status="failed", error=str(e))

    async def _validate(self, payload: dict) -> TaskResult:
        table = payload.get("table", "")
        checks = payload.get("checks", [])
        results = []
        try:
            con = get_duckdb_connection()
            for check in checks:
                check_type = check.get("type")
                column = check.get("column")
                if check_type == "not_null":
                    nulls = con.execute(f"SELECT count(*) FROM {table} WHERE {column} IS NULL").fetchone()[0]
                    results.append({"check": f"{column} NOT NULL", "passed": nulls == 0, "null_count": nulls})
                elif check_type == "unique":
                    total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    unique = con.execute(f"SELECT count(DISTINCT {column}) FROM {table}").fetchone()[0]
                    results.append({"check": f"{column} UNIQUE", "passed": total == unique, "total": total, "unique": unique})
            failed = [r for r in results if not r["passed"]]
            return TaskResult(task_id=task.task_id, status="completed" if not failed else "failed", output={
                "table": table, "checks": results, "passed": len(results) - len(failed), "failed": len(failed)
            })
        except Exception as e:
            return TaskResult(task_id=task.task_id, status="failed", error=str(e))

    async def _export(self, payload: dict) -> TaskResult:
        table = payload.get("table", "")
        format = payload.get("format", "parquet")
        output_path = payload.get("output_path", f"exports/{table}.{format}")
        try:
            con = get_duckdb_connection()
            if format == "parquet":
                con.execute(f"COPY {table} TO '{output_path}' (FORMAT PARQUET)")
            else:
                con.execute(f"COPY {table} TO '{output_path}' (FORMAT CSV, HEADER)")
            return TaskResult(task_id=task.task_id, status="completed", output={"path": output_path})
        except Exception as e:
            return TaskResult(task_id=task.task_id, status="failed", error=str(e))

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
