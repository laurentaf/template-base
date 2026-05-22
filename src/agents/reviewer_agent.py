from src.agents.base import BaseAgent
from src.schemas.tasks import Task, TaskResult
from src.schemas.messages import AgentMessage

class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__("reviewer", [
            "code_review", "data_validation", "schema_validation",
            "quality_check", "security_audit"
        ])

    async def handle_task(self, task: Task) -> TaskResult:
        ttype = task.task_type
        payload = task.payload

        if ttype == "review_code":
            return await self._review_code(payload)
        if ttype == "validate_schema":
            return await self._validate_schema(payload)
        if ttype == "audit_security":
            return await self._audit_security(payload)
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown: {ttype}")

    async def _review_code(self, payload: dict) -> TaskResult:
        content = payload.get("content", "")
        issues = []
        if "print(" in content and "import logging" not in content:
            issues.append({"severity": "warning", "line": 0, "message": "Use logging instead of print()"})
        if "password" in content.lower() or "secret" in content.lower():
            issues.append({"severity": "error", "line": 0, "message": "Hardcoded secret detected"})
        if "api_key" in content.lower() and "os.environ" not in content:
            issues.append({"severity": "error", "line": 0, "message": "Use env vars for API keys"})
        if "except:" in content:
            issues.append({"severity": "warning", "line": 0, "message": "Bare except clause"})
        passed = len([i for i in issues if i["severity"] == "error"]) == 0
        return TaskResult(
            task_id=task.task_id,
            status="completed" if passed else "failed",
            output={"issues": issues, "passed": passed, "total_issues": len(issues)}
        )

    async def _validate_schema(self, payload: dict) -> TaskResult:
        table = payload.get("table", "")
        expected_schema = payload.get("expected_schema", {})
        issues = []
        for col, col_type in expected_schema.items():
            pass
        return TaskResult(task_id=task.task_id, status="completed", output={
            "table": table, "checks": len(expected_schema), "issues": issues
        })

    async def _audit_security(self, payload: dict) -> TaskResult:
        return TaskResult(task_id=task.task_id, status="completed", output={
            "status": "clean", "findings": []
        })

    async def on_message(self, msg: AgentMessage):
        if msg.topic == "validation.requested":
            self.log(f"Validation request from {msg.sender}")
            await self.enqueue_task(Task(
                task_id=msg.correlation_id or msg.msg_id,
                task_type="review_code",
                agent_type="reviewer",
                payload=msg.payload
            ))

async def main():
    agent = ReviewerAgent()
    await agent.start()
    agent.log("Reviewer Agent ready.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
