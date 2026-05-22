from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime

class AgentMessage(BaseModel):
    msg_id: str
    msg_type: str  # request, response, event, broadcast
    topic: str     # task.completed, state.updated, validation.requested, etc.
    sender: str
    recipient: Optional[str] = None
    payload: dict[str, Any] = {}
    correlation_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class AgentEvent(BaseModel):
    event: str
    agent_id: str
    agent_type: str
    payload: dict[str, Any] = {}
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
