import asyncio

from src.agents.base import BaseAgent
from src.core.llm import llm
from src.schemas.tasks import Task, TaskResult
from src.tools.database import get_duckdb_connection


class AnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "analytics",
            [
                "analytics",
                "reporting",
                "query",
                "aggregation",
                "anomaly_detection",
                "dashboard",
            ],
        )

    async def handle_task(self, task: Task) -> TaskResult:
        ttype = task.task_type
        payload = task.payload

        if ttype == "aggregate":
            return await self._aggregate(payload, task.task_id)
        if ttype == "detect_anomalies":
            return await self._detect_anomalies(payload, task.task_id)
        if ttype == "generate_report":
            return await self._generate_report(payload, task.task_id)
        if ttype == "describe_dataset":
            return await self._describe_dataset(payload, task.task_id)
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown: {ttype}")

    async def _aggregate(self, payload: dict, task_id: str) -> TaskResult:
        table = payload.get("table", "")
        measures = payload.get("measures", ["count(*)"])
        group_by = payload.get("group_by", [])
        db_path = payload.get("db_path", "data/silver.duckdb")
        layer = payload.get("layer", "silver")
        measures_sql = ", ".join(measures)
        group_sql = ", ".join(group_by) if group_by else ""
        query = f"SELECT {measures_sql} FROM {layer}.{table}"
        if group_sql:
            query += f" GROUP BY {group_sql}"
        try:
            con = get_duckdb_connection(db_path)
            result = con.execute(query).fetchdf()
            con.close()
            return TaskResult(
                task_id=task_id,
                status="completed",
                output={
                    "rows": len(result),
                    "data": result.to_dict(orient="records"),
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _detect_anomalies(self, payload: dict, task_id: str) -> TaskResult:
        table = payload.get("table", "")
        column = payload.get("column", "")
        threshold = payload.get("zscore_threshold", 3.0)
        db_path = payload.get("db_path", "data/silver.duckdb")
        layer = payload.get("layer", "silver")
        query = f"""
            WITH stats AS (
                SELECT avg({column}) AS mean, stddev({column}) AS std FROM {layer}.{table}
            )
            SELECT *, ({column} - mean) / NULLIF(std, 0) AS zscore
            FROM {layer}.{table}, stats
            WHERE abs(({column} - mean) / NULLIF(std, 0)) > {threshold}
        """
        try:
            con = get_duckdb_connection(db_path)
            result = con.execute(query).fetchdf()
            con.close()
            return TaskResult(
                task_id=task_id,
                status="completed",
                output={
                    "anomalies": len(result),
                    "details": result.to_dict(orient="records")[:100],
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _generate_report(self, payload: dict, task_id: str) -> TaskResult:
        tables = payload.get("tables", [])
        db_path = payload.get("db_path", "data/silver.duckdb")
        table_summaries = []
        for table in tables:
            try:
                con = get_duckdb_connection(db_path)
                count = con.execute(f"SELECT count(*) FROM silver.{table}").fetchone()[0]
                cols = con.execute(
                    f"SELECT column_name, data_type FROM information_schema.columns "
                    f"WHERE table_name = '{table}' AND table_schema = 'silver'"
                ).fetchall()
                con.close()
                col_desc = "\n".join(f"  - {c[0]}: {c[1]}" for c in cols)
                table_summaries.append(
                    f"Table: silver.{table}\n  Rows: {count}\nColumns:\n{col_desc}"
                )
            except Exception as e:
                table_summaries.append(f"Table: {table}\n  Error: {e}")

        prompt = (
            "Generate a data analysis report in markdown based on these table summaries:\n\n"
            + "\n---\n".join(table_summaries)
        )
        resp = llm.chat([{"role": "user", "content": prompt}])
        return TaskResult(
            task_id=task_id,
            status="completed",
            output={
                "report": resp.content,
                "tables": tables,
                "model": resp.model,
            },
        )

    async def _describe_dataset(self, payload: dict, task_id: str) -> TaskResult:
        table = payload.get("table", "")
        db_path = payload.get("db_path", "data/silver.duckdb")
        layer = payload.get("layer", "silver")
        try:
            con = get_duckdb_connection(db_path)
            count = con.execute(f"SELECT count(*) FROM {layer}.{table}").fetchone()[0]
            cols = con.execute(
                f"SELECT column_name, data_type FROM information_schema.columns "
                f"WHERE table_name = '{table}' AND table_schema = '{layer}'"
            ).fetchall()
            profiles = []
            for col, dtype in cols:
                nulls = con.execute(
                    f"SELECT count(*) FROM {layer}.{table} WHERE {col} IS NULL"
                ).fetchone()[0]
                distinct = con.execute(
                    f"SELECT count(DISTINCT {col}) FROM {layer}.{table}"
                ).fetchone()[0]
                profiles.append(
                    {"column": col, "type": dtype, "nulls": nulls, "distinct": distinct}
                )
            con.close()
            prompt = (
                f"Dataset: {layer}.{table}\n"
                f"Total rows: {count}\n"
                f"Columns:\n"
                + "\n".join(
                    f"  - {p['column']}: {p['type']} (nulls: {p['nulls']}, distinct: {p['distinct']})"
                    for p in profiles
                )
                + "\n\nDescribe this dataset: what each column likely represents, "
                "data quality observations, and potential use cases."
            )
            resp = llm.chat([{"role": "user", "content": prompt}])
            return TaskResult(
                task_id=task_id,
                status="completed",
                output={
                    "table": table,
                    "rows": count,
                    "columns": profiles,
                    "description": resp.content,
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))


async def main():
    agent = AnalyticsAgent()
    await agent.start()
    agent.log("Analytics Agent ready.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
