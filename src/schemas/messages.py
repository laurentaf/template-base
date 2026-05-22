from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    msg_id: str
    msg_type: str  # request, response, event, broadcast
    topic: str  # task.completed, state.updated, validation.requested, etc.
    sender: str
    recipient: str | None = None
    payload: dict[str, Any] = {}
    correlation_id: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class AgentEvent(BaseModel):
    event: str
    agent_id: str
    agent_type: str
    payload: dict[str, Any] = {}
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
