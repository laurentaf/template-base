import json
from pathlib import Path

from src.schemas.decisions import DecisionLog, DecisionStatus


class DecisionLogStore:
    def __init__(self, path: str = "docs/decisions.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path) as f:
            return json.load(f)

    def _save(self, data: list[dict]):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def add(self, decision: DecisionLog):
        data = self._load()
        data.append(decision.model_dump())
        self._save(data)

    def all(self) -> list[DecisionLog]:
        return [DecisionLog(**d) for d in self._load()]

    def by_status(self, status: DecisionStatus) -> list[DecisionLog]:
        return [d for d in self.all() if d.status == status]

    def by_phase(self, phase: str) -> list[DecisionLog]:
        return [d for d in self.all() if d.sdd_phase == phase]

    def by_feature(self, feature: str) -> list[DecisionLog]:
        return [d for d in self.all() if d.feature == feature]

    def next_id(self) -> str:
        existing = self._load()
        n = len([d for d in existing if d.get("id", "").startswith("ADR-")])
        return f"ADR-{n + 1:03d}"

    def status_summary(self) -> dict:
        all_d = self.all()
        return {
            "total": len(all_d),
            "proposed": len([d for d in all_d if d.status == DecisionStatus.proposed]),
            "accepted": len([d for d in all_d if d.status == DecisionStatus.accepted]),
            "deprecated": len([d for d in all_d if d.status == DecisionStatus.deprecated]),
            "superseded": len([d for d in all_d if d.status == DecisionStatus.superseded]),
            "file": str(self.path),
        }
