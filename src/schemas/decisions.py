from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DecisionStatus(StrEnum):
    proposed = "proposed"
    accepted = "accepted"
    deprecated = "deprecated"
    superseded = "superseded"


class DecisionLog(BaseModel):
    id: str
    title: str
    status: DecisionStatus
    context: str
    decision: str
    consequences: str
    alternatives: list[str] = []
    sdd_phase: str
    date: str = Field(default_factory=lambda: datetime.now().isoformat())
    author: str = "ai-agent"
    tags: list[str] = []
    workflow_id: str | None = None
    feature: str | None = None
