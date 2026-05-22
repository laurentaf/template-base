from src.agents.base import BaseAgent
from src.schemas.tasks import Task, TaskResult
from src.schemas.messages import AgentMessage

class CodeGenAgent(BaseAgent):
    def __init__(self):
        super().__init__("code-gen", [
            "code_generation", "dbt_model", "sql_generation",
            "pipeline_code", "scaffold"
        ])

    async def handle_task(self, task: Task) -> TaskResult:
        ttype = task.task_type
        payload = task.payload

        if ttype == "generate_dbt_model":
            return await self._generate_dbt_model(payload)
        if ttype == "generate_pipeline":
            return await self._generate_pipeline(payload)
        if ttype == "generate_sql":
            return await self._generate_sql(payload)
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown: {ttype}")

    async def _generate_dbt_model(self, payload: dict) -> TaskResult:
        model_name = payload.get("name", "model")
        sql = payload.get("sql", "")
        materialized = payload.get("materialized", "view")
        model_code = f"""-- dbt model: {model_name}
-- materialized: {materialized}

{{{{ config(materialized='{materialized}') }}}}

{'' if sql else '-- TODO: define SQL'}
{sql}"""
        return TaskResult(task_id=task.task_id, status="completed", output={"file": f"transform/models/{model_name}.sql", "content": model_code})

    async def _generate_pipeline(self, payload: dict) -> TaskResult:
        name = payload.get("name", "pipeline")
        source = payload.get("source", "csv")
        target = payload.get("target", "postgres")
        code = f'''"""Pipeline: {name}"""
import duckdb
from src.tools.database import get_duckdb_connection, get_postgres_engine

def run():
    con = get_duckdb_connection()
    # Source: {source}
    # Target: {target}
    con.execute("SELECT 1")
    print(f"Pipeline '{name}' complete")

if __name__ == "__main__":
    run()
'''
        return TaskResult(task_id=task.task_id, status="completed", output={
            "file": f"src/pipelines/{name}.py", "content": code
        })

    async def _generate_sql(self, payload: dict) -> TaskResult:
        description = payload.get("description", "")
        dialect = payload.get("dialect", "duckdb")
        sql = f"-- Auto-generated SQL ({dialect})\n-- Description: {description}\nSELECT 1;"
        return TaskResult(task_id=task.task_id, status="completed", output={"sql": sql})

    async def on_message(self, msg: AgentMessage):
        if msg.topic == "generation.requested":
            self.log(f"Generation request from {msg.sender}: {msg.payload.get('type')}")
            # Auto-enqueue a self task
            payload = msg.payload
            await self.enqueue_task(Task(
                task_type=f"generate_{payload.get('type', 'pipeline')}",
                agent_type="code-gen",
                task_id=msg.correlation_id or msg.msg_id,
                payload=payload
            ))

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
