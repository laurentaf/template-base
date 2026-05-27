import asyncio

from src.agents.base import BaseAgent
from src.core.llm import llm
from src.schemas.messages import AgentMessage
from src.schemas.tasks import Task, TaskResult


class CodeGenAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "code-gen",
            ["code_generation", "dbt_model", "sql_generation", "pipeline_code", "scaffold"],
        )

    async def handle_task(self, task: Task) -> TaskResult:
        ttype = task.task_type
        payload = task.payload

        if ttype == "generate_dbt_model":
            return await self._generate_dbt_model(payload, task.task_id)
        if ttype == "generate_pipeline":
            return await self._generate_pipeline(payload, task.task_id)
        if ttype == "generate_sql":
            return await self._generate_sql(payload, task.task_id)
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown: {ttype}")

    async def _generate_dbt_model(self, payload: dict, task_id: str) -> TaskResult:
        model_name = payload.get("name", "model")
        sql = payload.get("sql", "")
        materialized = payload.get("materialized", "view")
        description = payload.get("description", "")
        if not sql and description:
            try:
                prompt = (
                    f"Generate a dbt SQL model named '{model_name}' "
                    f"(materialized: {materialized}) for: {description}\n"
                    "Output only the SQL SELECT statement, no explanation."
                )
                resp = await llm.chat_async([{"role": "user", "content": prompt}])
                sql = resp.content.strip()
            except Exception:
                sql = f"-- TODO: define SQL for {description}"
        model_code = f"""-- dbt model: {model_name}
-- materialized: {materialized}

{{{{ config(materialized='{materialized}') }}}}

{sql}"""
        return TaskResult(
            task_id=task_id,
            status="completed",
            output={"file": f"transform/models/{model_name}.sql", "content": model_code},
        )

    async def _generate_pipeline(self, payload: dict, task_id: str) -> TaskResult:
        name = payload.get("name", "pipeline")
        source = payload.get("source", "csv")
        target = payload.get("target", "postgres")
        description = payload.get("description", "")
        code = ""
        try:
            prompt = (
                f"Generate a Python ETL pipeline named '{name}' "
                f"that reads from {source} and writes to {target}.\n"
                f"Context: {description}\n"
                "Use duckdb and the project's src.tools.database helpers. "
                "Output only the Python code, no explanation."
            )
            resp = await llm.chat_async([{"role": "user", "content": prompt}])
            code = resp.content.strip()
            if code.startswith("```"):
                code = "\n".join(code.split("\n")[1:-1])
        except Exception:
            code = f'"""Pipeline: {name}"""\n# TODO: implement {source} -> {target}\n'
        return TaskResult(
            task_id=task_id,
            status="completed",
            output={"file": f"src/pipelines/{name}.py", "content": code},
        )

    async def _generate_sql(self, payload: dict, task_id: str) -> TaskResult:
        description = payload.get("description", "")
        dialect = payload.get("dialect", "duckdb")
        sql = ""
        try:
            prompt = (
                f"Generate {dialect} SQL for: {description}\nOutput only the SQL, no explanation."
            )
            resp = await llm.chat_async([{"role": "user", "content": prompt}])
            sql = resp.content.strip()
            if sql.startswith("```"):
                sql = "\n".join(sql.split("\n")[1:-1])
        except Exception:
            sql = f"-- Auto-generated SQL ({dialect})\n-- Description: {description}\nSELECT 1;"
        return TaskResult(task_id=task_id, status="completed", output={"sql": sql})

    async def on_message(self, msg: AgentMessage):
        if msg.topic == "generation.requested":
            self.log(f"Generation request from {msg.sender}: {msg.payload.get('type')}")
            payload = msg.payload
            await self.enqueue_task(
                Task(
                    task_type=f"generate_{payload.get('type', 'pipeline')}",
                    agent_type="code-gen",
                    task_id=msg.correlation_id or msg.msg_id,
                    payload=payload,
                )
            )


async def main():
    agent = CodeGenAgent()
    await agent.start()
    agent.log("Code Gen Agent ready.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
