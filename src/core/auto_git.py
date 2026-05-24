"""Automatic Git Workflow.

After every task completion (configurable):
1. Stage changed files
2. Generate commit message from task description
3. Commit with conventional commit format
4. On feature completion: optionally create PR via GitHub
"""

import subprocess
from typing import Any

from src.core.config import settings


class AutoGit:
    @staticmethod
    def is_enabled() -> bool:
        return settings.AUTO_GIT

    @staticmethod
    def has_changes() -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=10,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    @staticmethod
    def stage_all():
        try:
            subprocess.run(["git", "add", "-A"], capture_output=True, timeout=30)
        except Exception:
            pass

    @staticmethod
    def generate_commit_message(
        task_type: str,
        task_result: dict[str, Any] | None = None,
        agent_type: str = "",
    ) -> str:
        prefix_map = {
            "run_query": "feat(data)",
            "ingest_file": "feat(data)",
            "transform": "feat(data)",
            "validate": "test(data)",
            "validate_all": "test(data)",
            "export": "feat(data)",
            "run_medallion": "feat(pipeline)",
            "bronze_ingest": "feat(pipeline)",
            "silver_transform": "feat(pipeline)",
            "gold_aggregate": "feat(pipeline)",
            "aggregate": "feat(analytics)",
            "detect_anomalies": "feat(analytics)",
            "generate_report": "docs(analytics)",
            "describe_dataset": "docs(analytics)",
            "generate_dbt_model": "feat(code-gen)",
            "generate_pipeline": "feat(code-gen)",
            "generate_sql": "feat(code-gen)",
            "review_code": "style(review)",
            "validate_schema": "test(review)",
            "audit_security": "fix(security)",
            "run_workflow": "feat(workflow)",
            "check_health": "chore(health)",
        }

        prefix = prefix_map.get(task_type, "chore")
        if agent_type:
            prefix = prefix.replace(")", f":{agent_type})")

        summary = task_type.replace("_", " ")
        if task_result and isinstance(task_result, dict):
            if "rows" in task_result:
                summary += f" ({task_result['rows']} rows)"
            elif "table" in task_result:
                summary += f" ({task_result['table']})"
            elif "view" in task_result:
                summary += f" ({task_result['view']})"

        return f"{prefix}: {summary}"

    @staticmethod
    def commit(message: str) -> bool:
        try:
            subprocess.run(
                ["git", "commit", "-m", message, "--no-verify"],
                capture_output=True, timeout=30,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def auto_commit(
        task_type: str,
        task_result: dict[str, Any] | None = None,
        agent_type: str = "",
    ):
        if not AutoGit.is_enabled():
            return
        if not AutoGit.has_changes():
            return

        AutoGit.stage_all()
        message = AutoGit.generate_commit_message(task_type, task_result, agent_type)
        AutoGit.commit(message)

    @staticmethod
    def create_branch(branch_name: str) -> bool:
        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                capture_output=True, timeout=10,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def push(remote: str = "origin", branch: str = "") -> bool:
        try:
            cmd = ["git", "push", remote]
            if branch:
                cmd.append(branch)
            subprocess.run(cmd, capture_output=True, timeout=60)
            return True
        except Exception:
            return False

    @staticmethod
    def create_pr(title: str, body: str = "", base: str = "main") -> bool:
        try:
            cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]
            subprocess.run(cmd, capture_output=True, timeout=30)
            return True
        except Exception:
            return False


auto_git = AutoGit()
