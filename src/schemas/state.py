from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime

class AgentState(BaseModel):
    agent_id: str
    agent_type: str
    status: str = "idle"  # idle, busy, error, offline
    capabilities: list[str] = []
    current_task_id: Optional[str] = None
    last_heartbeat: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1

class TaskState(BaseModel):
    task_id: str
    parent_task_id: Optional[str] = None
    workflow_id: str
    agent_type: str
    status: str = "pending"  # pending, assigned, running, completed, failed, retrying
    payload: dict[str, Any] = {}
    result: Optional[Any] = None
    error: Optional[str] = None
    assigned_to: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    version: int = 1

class WorkflowState(BaseModel):
    workflow_id: str
    name: str
    status: str = "pending"  # pending, running, completed, failed
    dag: list[dict[str, Any]] = []  # list of task definitions with dependencies
    task_ids: list[str] = []
    context: dict[str, Any] = {}
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    version: int = 1

class ProjectState(BaseModel):
    project_name: str
    github_url: Optional[str] = None
    active_workflows: list[str] = []
    completed_workflows: list[str] = []
    metadata: dict[str, Any] = {}
    version: int = 1
