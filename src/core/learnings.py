"""Learning Emitter — Local Learning Capture for Self-Evolution.

Each project emits learnings to .learnings/ directory.
The global EvolveEngine harvests these periodically and applies
improvements back to the template-base.

Learning Categories:
  - kb_insight: New knowledge discovered
      (e.g., "DuckDB VSS requires float32 for embeddings")
  - agent_improvement: Better agent behavior observed
      (e.g., "Reviewer should check SQL injection")
  - config_tuning: Better default configs found
      (e.g., "REDIS_URL should use db=1 for tasks")
  - pattern_discovered: Reusable pattern found
      (e.g., "Medallion works best with date partitioning")
  - error_resolution: How an error was resolved
      (e.g., "telemetry crash fixed by deferring import")
  - workflow_optimization: Better workflow pattern
      (e.g., "Parallel dispatch 3x faster for validation")
"""

import json
import uuid
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class LearningCategory(StrEnum):
    KB_INSIGHT = "kb_insight"
    AGENT_IMPROVEMENT = "agent_improvement"
    CONFIG_TUNING = "config_tuning"
    PATTERN_DISCOVERED = "pattern_discovered"
    ERROR_RESOLUTION = "error_resolution"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"


class Learning(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    category: LearningCategory
    domain: str = ""
    title: str
    body: str
    confidence: float = 0.0
    project_name: str = ""
    source_agent: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearningEmitter:
    def __init__(self, project_root: str | Path | None = None):
        self.root = Path(project_root or ".")
        self.learnings_dir = self.root / ".learnings"
        self.index_path = self.learnings_dir / "index.json"

    def _ensure_dir(self):
        self.learnings_dir.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        category: LearningCategory,
        title: str,
        body: str,
        domain: str = "",
        confidence: float = 0.0,
        project_name: str = "",
        source_agent: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Learning:
        learning = Learning(
            category=category,
            domain=domain,
            title=title,
            body=body,
            confidence=confidence,
            project_name=project_name,
            source_agent=source_agent,
            metadata=metadata or {},
        )
        self._ensure_dir()
        filepath = self.learnings_dir / f"{learning.id}.json"
        filepath.write_text(
            learning.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        self._update_index(learning)
        return learning

    def _update_index(self, learning: Learning):
        index = self.load_index()
        index.append(
            {
                "id": learning.id,
                "timestamp": learning.timestamp,
                "category": learning.category.value,
                "domain": learning.domain,
                "title": learning.title,
                "confidence": learning.confidence,
                "project": learning.project_name,
                "agent": learning.source_agent,
            }
        )
        self.index_path.write_text(
            json.dumps(index, indent=2) + "\n",
            encoding="utf-8",
        )

    def load_index(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def load_learning(self, learning_id: str) -> Learning | None:
        filepath = self.learnings_dir / f"{learning_id}.json"
        if not filepath.exists():
            return None
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return Learning(**data)
        except Exception:
            return None

    def load_all(self) -> list[Learning]:
        index = self.load_index()
        results: list[Learning] = []
        for entry in index:
            learning = self.load_learning(entry["id"])
            if learning:
                results.append(learning)
        return results

    def load_since(self, since_iso: str) -> list[Learning]:
        return [learning for learning in self.load_all() if learning.timestamp >= since_iso]

    def prune_applied(self, applied_ids: list[str]):
        for lid in applied_ids:
            filepath = self.learnings_dir / f"{lid}.json"
            if filepath.exists():
                filepath.unlink()
        remaining = [e for e in self.load_index() if e["id"] not in applied_ids]
        self._ensure_dir()
        self.index_path.write_text(
            json.dumps(remaining, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def emit_from_task_result(
        task_type: str,
        task_result: dict[str, Any],
        agent_type: str,
        project_name: str = "",
        project_root: str | Path | None = None,
    ) -> Learning | None:
        """Auto-extract a learning from a task result if noteworthy."""
        emitter = LearningEmitter(project_root=project_root)
        category = LearningEmitter._infer_category(task_type, task_result)
        if category is None:
            return None
        domain = LearningEmitter._infer_domain(task_type, agent_type)
        title = LearningEmitter._infer_title(task_type, task_result, agent_type)
        body = LearningEmitter._build_body(task_type, task_result, agent_type)
        confidence = LearningEmitter._infer_confidence(task_result)
        return emitter.emit(
            category=category,
            domain=domain,
            title=title,
            body=body,
            confidence=confidence,
            project_name=project_name,
            source_agent=agent_type,
            metadata={"task_type": task_type},
        )

    @staticmethod
    def _infer_category(
        task_type: str,
        result: dict[str, Any],
    ) -> LearningCategory | None:
        if "error" in result:
            return LearningCategory.ERROR_RESOLUTION
        if task_type in ("validate", "validate_all", "review_code", "audit_security"):
            return LearningCategory.AGENT_IMPROVEMENT
        if task_type in ("run_query", "run_medallion", "aggregate"):
            return LearningCategory.PATTERN_DISCOVERED
        if task_type in ("check_health", "plan_project"):
            return LearningCategory.WORKFLOW_OPTIMIZATION
        if task_type in ("ingest_file", "transform", "export"):
            return LearningCategory.KB_INSIGHT
        if task_type in ("generate_dbt_model", "generate_pipeline"):
            return LearningCategory.CONFIG_TUNING
        return None

    @staticmethod
    def _infer_domain(task_type: str, agent_type: str) -> str:
        domain_map = {
            "data-pipeline": "medallion",
            "analytics": "duckdb",
            "code-gen": "dbt",
            "reviewer": "data-quality",
            "orchestrator": "consensus",
        }
        return domain_map.get(agent_type, "python")

    @staticmethod
    def _infer_title(
        task_type: str,
        result: dict[str, Any],
        agent_type: str,
    ) -> str:
        if "error" in result:
            return f"Error in {task_type}: {str(result['error'])[:80]}"
        if "rows" in result:
            return f"{task_type} produced {result['rows']} rows"
        if "table" in result:
            return f"{task_type} on {result['table']}"
        return f"{agent_type}: {task_type} completed"

    @staticmethod
    def _build_body(
        task_type: str,
        result: dict[str, Any],
        agent_type: str,
    ) -> str:
        if "error" in result:
            return f"Task {task_type} by {agent_type} failed: {result['error']}"
        parts = [f"Task: {task_type}", f"Agent: {agent_type}"]
        for key in ("rows", "table", "view", "report", "description"):
            if key in result:
                val = str(result[key])[:300]
                parts.append(f"{key}: {val}")
        return "\n".join(parts)

    @staticmethod
    def _infer_confidence(result: dict[str, Any]) -> float:
        if "error" in result:
            return 0.3
        if result.get("rows", 0) > 0:
            return 0.8
        return 0.6


learning_emitter = LearningEmitter()
