from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentState(BaseModel):
    agent_id: str
    agent_type: str
    status: str = "idle"  # idle, busy, error, offline
    capabilities: list[str] = []
    current_task_id: str | None = None
    last_heartbeat: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


class TaskState(BaseModel):
    task_id: str
    parent_task_id: str | None = None
    workflow_id: str
    agent_type: str
    status: str = "pending"  # pending, assigned, running, completed, failed, retrying
    payload: dict[str, Any] = {}
    result: Any | None = None
    error: str | None = None
    assigned_to: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    version: int = 1


class WorkflowState(BaseModel):
    workflow_id: str
    name: str
    status: str = "pending"  # pending, running, completed, failed
    dag: list[dict[str, Any]] = []  # list of task definitions with dependencies
    task_ids: list[str] = []
    context: dict[str, Any] = {}
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    version: int = 1


class ProjectState(BaseModel):
    project_name: str
    github_url: str | None = None
    active_workflows: list[str] = []
    completed_workflows: list[str] = []
    metadata: dict[str, Any] = {}
    version: int = 1
