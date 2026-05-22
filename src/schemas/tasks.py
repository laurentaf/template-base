from typing import Any

from pydantic import BaseModel


class Task(BaseModel):
    task_id: str
    task_type: str
    agent_type: str
    payload: dict[str, Any] = {}
    priority: int = 0
    max_retries: int = 3
    depends_on: list[str] = []


class TaskResult(BaseModel):
    task_id: str
    status: str  # completed, failed, skipped
    output: Any | None = None
    error: str | None = None
    metrics: dict[str, Any] = {}


class WorkflowDefinition(BaseModel):
    workflow_id: str
    name: str
    description: str = ""
    tasks: list[Task] = []
    context: dict[str, Any] = {}
