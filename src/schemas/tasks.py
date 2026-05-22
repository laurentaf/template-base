from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime

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
    output: Optional[Any] = None
    error: Optional[str] = None
    metrics: dict[str, Any] = {}

class WorkflowDefinition(BaseModel):
    workflow_id: str
    name: str
    description: str = ""
    tasks: list[Task] = []
    context: dict[str, Any] = {}
