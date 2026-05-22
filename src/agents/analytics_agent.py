import duckdb
from src.agents.base import BaseAgent
from src.schemas.tasks import Task, TaskResult
from src.schemas.messages import AgentMessage

class AnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__("analytics", [
            "analytics", "reporting", "query", "aggregation",
            "anomaly_detection", "dashboard"
        ])

    async def handle_task(self, task: Task) -> TaskResult:
        ttype = task.task_type
        payload = task.payload

        if ttype == "aggregate":
            return await self._aggregate(payload)
        if ttype == "detect_anomalies":
            return await self._detect_anomalies(payload)
        if ttype == "generate_report":
            return await self._generate_report(payload)
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown: {ttype}")

    async def _aggregate(self, payload: dict) -> TaskResult:
        import duckdb
        table = payload.get("table", "")
        measures = payload.get("measures", ["count(*)"])
        group_by = payload.get("group_by", [])
        measures_sql = ", ".join(measures)
        group_sql = ", ".join(group_by) if group_by else ""
        query = f"SELECT {measures_sql} FROM {table}"
        if group_sql:
            query += f" GROUP BY {group_sql}"
        try:
            con = duckdb.connect(":memory:")
            con.execute(f"ATTACH '' AS template_db (TYPE duckdb)")
            result = con.execute(query).fetchdf()
            return TaskResult(task_id=task.task_id, status="completed", output=result.to_dict(orient="records"))
        except Exception as e:
            return TaskResult(task_id=task.task_id, status="failed", error=str(e))

    async def _detect_anomalies(self, payload: dict) -> TaskResult:
        import duckdb
        table = payload.get("table", "")
        column = payload.get("column", "")
        threshold = payload.get("zscore_threshold", 3.0)
        query = f"""
            WITH stats AS (
                SELECT avg({column}) AS mean, stddev({column}) AS std FROM {table}
            )
            SELECT *, ({column} - mean) / NULLIF(std, 0) AS zscore
            FROM {table}, stats
            WHERE abs(({column} - mean) / NULLIF(std, 0)) > {threshold}
        """
        try:
            con = duckdb.connect(":memory:")
            result = con.execute(query).fetchdf()
            return TaskResult(task_id=task.task_id, status="completed", output={
                "anomalies": len(result),
                "details": result.to_dict(orient="records")[:100]
            })
        except Exception as e:
            return TaskResult(task_id=task.task_id, status="failed", error=str(e))

    async def _generate_report(self, payload: dict) -> TaskResult:
        tables = payload.get("tables", [])
        report = {"tables_analyzed": tables, "summary": {}, "generated_at": None}
        from datetime import datetime
        report["generated_at"] = datetime.now().isoformat()
        return TaskResult(task_id=task.task_id, status="completed", output=report)

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
