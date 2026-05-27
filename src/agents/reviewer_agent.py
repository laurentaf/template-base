import asyncio
import os

from src.agents.base import BaseAgent
from src.schemas.messages import AgentMessage
from src.schemas.tasks import Task, TaskResult
from src.tools.database import (
    get_duckdb_connection,
    get_postgres_engine,
    safe_column,
    safe_layer,
    safe_table,
)


class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "reviewer",
            [
                "code_review",
                "data_validation",
                "schema_validation",
                "quality_check",
                "security_audit",
            ],
        )

    async def handle_task(self, task: Task) -> TaskResult:
        ttype = task.task_type
        payload = task.payload

        if ttype == "review_code":
            return await self._review_code(payload, task.task_id)
        if ttype == "validate_schema":
            return await self._validate_schema(payload, task.task_id)
        if ttype == "audit_security":
            return await self._audit_security(payload, task.task_id)
        if ttype == "validate_table":
            return await self._validate_table(payload, task.task_id)
        return TaskResult(task_id=task.task_id, status="failed", error=f"Unknown: {ttype}")

    async def _review_code(self, payload: dict, task_id: str) -> TaskResult:
        content = payload.get("content", "")
        file_path = payload.get("file_path", "")
        issues = []
        if "print(" in content and "import logging" not in content:
            issues.append({"severity": "warning", "message": "Use logging instead of print()"})
        if "password" in content.lower() or "secret" in content.lower():
            issues.append({"severity": "error", "message": "Hardcoded secret detected"})
        if (
            "api_key" in content.lower()
            and "os.environ" not in content
            and "os.getenv" not in content
        ):
            issues.append({"severity": "error", "message": "Use env vars for API keys"})
        if "except:" in content:
            issues.append({"severity": "warning", "message": "Bare except clause"})
        if "eval(" in content or "exec(" in content:
            issues.append({"severity": "error", "message": "Avoid eval/exec"})
        if "import *" in content:
            issues.append({"severity": "warning", "message": "Avoid wildcard imports"})
        hardcoded_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
        for host in hardcoded_hosts:
            if host in content and "HOST" not in content and "config" not in content.lower():
                issues.append({"severity": "info", "message": f"Hardcoded host '{host}'"})
        passed = len([i for i in issues if i["severity"] == "error"]) == 0
        return TaskResult(
            task_id=task_id,
            status="completed" if passed else "failed",
            output={
                "file": file_path,
                "issues": issues,
                "passed": passed,
                "total_issues": len(issues),
            },
        )

    async def _validate_schema(self, payload: dict, task_id: str) -> TaskResult:
        table = payload.get("table", "")
        expected_schema = payload.get("expected_schema", {})
        db_path = payload.get("db_path", "data/silver.duckdb")
        layer = payload.get("layer", "silver")
        source = payload.get("source", "duckdb")
        issues = []

        try:
            if source == "duckdb":
                con = get_duckdb_connection(db_path)
                actual_cols = {
                    r[0]: r[1]
                    for r in con.execute(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_name = ? AND table_schema = ?",
                        [table, layer],
                    ).fetchall()
                }
                con.close()
            else:
                engine = get_postgres_engine()
                result = engine.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = %s",
                    [table],
                ).fetchall()
                actual_cols = {r[0]: r[1] for r in result}

            missing = [c for c in expected_schema if c not in actual_cols]
            extra = [c for c in actual_cols if c not in expected_schema]
            type_mismatch = [
                f"{c}: expected {expected_schema[c]}, got {actual_cols[c]}"
                for c in expected_schema
                if c in actual_cols and expected_schema[c].lower() not in actual_cols[c].lower()
            ]
            for col in missing:
                issues.append({"severity": "error", "message": f"Missing column: {col}"})
            for col in extra:
                issues.append({"severity": "warning", "message": f"Unexpected column: {col}"})
            for mismatch in type_mismatch:
                issues.append({"severity": "error", "message": f"Type mismatch: {mismatch}"})

            passed = len([i for i in issues if i["severity"] == "error"]) == 0
            return TaskResult(
                task_id=task_id,
                status="completed" if passed else "failed",
                output={
                    "table": table,
                    "expected_cols": len(expected_schema),
                    "actual_cols": len(actual_cols),
                    "issues": issues,
                    "passed": passed,
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _validate_table(self, payload: dict, task_id: str) -> TaskResult:
        table = payload.get("table", "")
        db_path = payload.get("db_path", "data/silver.duckdb")
        layer = payload.get("layer", "silver")
        issues = []
        try:
            con = get_duckdb_connection(db_path)
            tref = f"{safe_layer(layer)}.{safe_table(table)}"
            count = con.execute(f"SELECT count(*) FROM {tref}").fetchone()[0]
            cols = con.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = ? AND table_schema = ?",
                [table, layer],
            ).fetchall()
            for col, dtype in cols:
                qcol = safe_column(col)
                nulls = con.execute(f"SELECT count(*) FROM {tref} WHERE {qcol} IS NULL").fetchone()[
                    0
                ]
                if nulls == count:
                    issues.append(
                        {"severity": "warning", "column": col, "message": "All values are NULL"}
                    )
                unique = con.execute(f"SELECT count(DISTINCT {qcol}) FROM {tref}").fetchone()[0]
                if unique == 1 and count > 1:
                    issues.append(
                        {
                            "severity": "info",
                            "column": col,
                            "message": "Only one distinct value — check if meaningful",
                        }
                    )
            con.close()
            passed = len([i for i in issues if i["severity"] == "error"]) == 0
            return TaskResult(
                task_id=task_id,
                status="completed" if passed else "failed",
                output={
                    "table": table,
                    "rows": count,
                    "columns": len(cols),
                    "issues": issues,
                    "passed": passed,
                },
            )
        except Exception as e:
            return TaskResult(task_id=task_id, status="failed", error=str(e))

    async def _audit_security(self, payload: dict, task_id: str) -> TaskResult:
        path = payload.get("path", ".")
        findings = []
        for root, dirs, files in os.walk(path):
            if ".venv" in root or "__pycache__" in root or ".git" in root:
                continue
            for f in files:
                if f.endswith((".py", ".env", ".yml", ".yaml", ".json", ".toml")):
                    fp = os.path.join(root, f)
                    try:
                        content = open(fp, errors="ignore").read()
                        if (
                            "password" in content.lower()
                            and "os.environ" not in content
                            and "os.getenv" not in content
                        ):
                            findings.append(
                                {
                                    "file": fp,
                                    "severity": "error",
                                    "message": "Possible hardcoded password",
                                }
                            )
                        if ".env" in f and "example" not in f.lower():
                            findings.append(
                                {
                                    "file": fp,
                                    "severity": "warning",
                                    "message": ".env file tracked in repo",
                                }
                            )
                    except Exception:
                        pass
        passed = len([f for f in findings if f["severity"] == "error"]) == 0
        return TaskResult(
            task_id=task_id,
            status="completed" if passed else "failed",
            output={
                "status": "clean" if passed else "issues_found",
                "findings": findings,
                "passed": passed,
            },
        )

    async def on_message(self, msg: AgentMessage):
        if msg.topic == "validation.requested":
            self.log(f"Validation request from {msg.sender}")
            await self.enqueue_task(
                Task(
                    task_id=msg.correlation_id or msg.msg_id,
                    task_type="review_code",
                    agent_type="reviewer",
                    payload=msg.payload,
                )
            )


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
