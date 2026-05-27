"""Evolve Engine — Global Self-Evolution for template-base.

Harvests learnings from all active projects and applies improvements
back to the template-base repository. This creates a feedback loop:

  Project A discovers pattern → EvolveEngine harvests → Template improves → Project B benefits

Global state directory: ~/.ltade/evolve/
  - projects.json  : Registry of active projects
  - learnings/     : Harvested learnings (JSON, organized by category)
  - applied/       : Log of applied improvements
  - rollback/      : Backups before changes

Usage:
  ltade evolve harvest   — Harvest learnings from all projects
  ltade evolve status    — Show evolution status
  ltade evolve apply     — Apply improvements to template
  ltade evolve rollback  — Undo last apply
"""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.core.config import settings
from src.core.learnings import Learning, LearningCategory, LearningEmitter
from src.core.llm import llm

EVOLVE_DIR = Path.home() / ".ltade" / "evolve"
PROJECTS_FILE = EVOLVE_DIR / "projects.json"
LEARNINGS_DIR = EVOLVE_DIR / "learnings"
APPLIED_DIR = EVOLVE_DIR / "applied"
ROLLBACK_DIR = EVOLVE_DIR / "rollback"


class ProjectEntry(BaseModel):
    path: str
    name: str = ""
    last_harvest: str = ""
    status: str = "active"
    learning_count: int = 0
    registered_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class AppliedChange(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    category: str
    title: str
    target_file: str
    description: str
    backup_path: str = ""


class EvolveEngine:
    def __init__(self, template_path: str | Path | None = None):
        self.template_path = Path(template_path or settings.template_path)
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in (EVOLVE_DIR, LEARNINGS_DIR, APPLIED_DIR, ROLLBACK_DIR):
            d.mkdir(parents=True, exist_ok=True)

    # ── Project Registry ──────────────────────────────────────

    def load_projects(self) -> list[ProjectEntry]:
        if not PROJECTS_FILE.exists():
            return []
        try:
            data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
            return [ProjectEntry(**e) for e in data]
        except Exception:
            return []

    def save_projects(self, projects: list[ProjectEntry]):
        PROJECTS_FILE.write_text(
            json.dumps([p.model_dump() for p in projects], indent=2) + "\n",
            encoding="utf-8",
        )

    def register_project(self, path: str, name: str = "") -> ProjectEntry:
        projects = self.load_projects()
        for p in projects:
            if p.path == str(Path(path).resolve()):
                return p
        entry = ProjectEntry(
            path=str(Path(path).resolve()),
            name=name or Path(path).resolve().name,
        )
        projects.append(entry)
        self.save_projects(projects)
        return entry

    def discover_projects(self) -> list[ProjectEntry]:
        """Auto-discover projects with .learnings/ directories."""
        known = {p.path for p in self.load_projects()}
        search_paths = [
            Path.home() / "projects",
            Path.cwd().parent,
        ]
        for search in search_paths:
            if not search.exists():
                continue
            for child in search.iterdir():
                if child.is_dir() and (child / ".learnings").exists():
                    resolved = str(child.resolve())
                    if resolved not in known:
                        self.register_project(resolved)
        return self.load_projects()

    # ── Harvest ───────────────────────────────────────────────

    def harvest(self, project_path: str) -> list[Learning]:
        """Harvest un-harvested learnings from a project."""
        emitter = LearningEmitter(project_root=project_path)
        projects = self.load_projects()
        last_harvest = ""
        for p in projects:
            if p.path == str(Path(project_path).resolve()):
                last_harvest = p.last_harvest
                break

        learnings = emitter.load_since(last_harvest) if last_harvest else emitter.load_all()

        for learning in learnings:
            dest = (
                LEARNINGS_DIR
                / learning.category.value
                / f"{learning.project_name}_{learning.id}.json"
            )
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(
                learning.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )

        for p in projects:
            if p.path == str(Path(project_path).resolve()):
                p.last_harvest = datetime.now().isoformat()
                p.learning_count = len(emitter.load_all())
                break
        self.save_projects(projects)
        return learnings

    def harvest_all(self) -> dict[str, list[Learning]]:
        """Harvest from all registered active projects."""
        results: dict[str, list[Learning]] = {}
        for p in self.load_projects():
            if p.status == "active":
                harvested = self.harvest(p.path)
                if harvested:
                    results[p.name] = harvested
        return results

    def load_harvested(self, category: str | None = None) -> list[Learning]:
        """Load all harvested learnings, optionally filtered by category."""
        learnings: list[Learning] = []
        dirs = (
            [LEARNINGS_DIR / category]
            if category
            else [LEARNINGS_DIR / c.value for c in LearningCategory]
        )
        for d in dirs:
            if not d.exists():
                continue
            for f in sorted(d.glob("*.json")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    learnings.append(Learning(**data))
                except Exception:
                    pass
        return learnings

    # ── Analyze ───────────────────────────────────────────────

    def analyze(self) -> dict[str, Any]:
        """Group and rank harvested learnings by category and domain."""
        learnings = self.load_harvested()
        by_category: dict[str, list[Learning]] = {}
        by_domain: dict[str, list[Learning]] = {}

        for learning in learnings:
            by_category.setdefault(learning.category.value, []).append(learning)
            if learning.domain:
                by_domain.setdefault(learning.domain, []).append(learning)

        high_value = [
            learning
            for learning in learnings
            if learning.confidence >= 0.7
            or learning.category
            in (
                LearningCategory.ERROR_RESOLUTION,
                LearningCategory.PATTERN_DISCOVERED,
            )
        ]

        return {
            "total": len(learnings),
            "by_category": {k: len(v) for k, v in by_category.items()},
            "by_domain": {k: len(v) for k, v in by_domain.items()},
            "high_value": len(high_value),
            "high_value_items": [
                {"id": learning.id, "title": learning.title, "category": learning.category.value}
                for learning in sorted(high_value, key=lambda x: x.confidence, reverse=True)[:10]
            ],
        }

    # ── Apply ─────────────────────────────────────────────────

    def _backup_file(self, filepath: Path) -> str:
        """Backup a file before modifying it. Returns backup path."""
        if not filepath.exists():
            return ""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{filepath.stem}_{stamp}{filepath.suffix}"
        backup_path = ROLLBACK_DIR / backup_name
        shutil.copy2(filepath, backup_path)
        return str(backup_path)

    def _log_applied(self, change: AppliedChange):
        log_file = APPLIED_DIR / f"{change.id}.json"
        log_file.write_text(change.model_dump_json(indent=2) + "\n", encoding="utf-8")

    def _generate_kb_article(self, learning: Learning) -> str:
        """Use LLM to generate a KB article from a learning."""
        prompt = (
            f"Generate a concise knowledge base article for the "
            f"'{learning.domain}' domain.\n\n"
            f"Title: {learning.title}\n"
            f"Category: {learning.category.value}\n"
            f"Confidence: {learning.confidence}\n"
            f"Details: {learning.body}\n"
            f"Source: {learning.source_agent} in {learning.project_name}\n\n"
            "Format as markdown. Include:\n"
            "- A clear heading\n"
            "- Key insight (1-2 sentences)\n"
            "- When to apply\n"
            "- Example if applicable\n"
            "Keep it under 50 lines."
        )
        try:
            resp = llm.chat([{"role": "user", "content": prompt}], max_tokens=1024)
            return resp.content
        except Exception:
            return f"# {learning.title}\n\n{learning.body}\n"

    def _apply_kb_insight(self, learnings: list[Learning]) -> list[AppliedChange]:
        changes: list[AppliedChange] = []
        for learning in learnings:
            if not learning.domain:
                continue
            concepts_dir = self.template_path / ".opencode" / "kb" / learning.domain / "concepts"
            concepts_dir.mkdir(parents=True, exist_ok=True)
            slug = learning.title.lower().replace(" ", "-").replace("/", "-")[:40]
            article_path = concepts_dir / f"{slug}.md"
            content = self._generate_kb_article(learning)

            if article_path.exists():
                backup = self._backup_file(article_path)
                existing = article_path.read_text(encoding="utf-8")
                content = existing + f"\n\n---\n\n{content}"
            else:
                backup = ""

            article_path.write_text(content, encoding="utf-8")
            change = AppliedChange(
                category=learning.category.value,
                title=learning.title,
                target_file=str(article_path.relative_to(self.template_path)),
                description=f"KB article from {learning.project_name}",
                backup_path=backup,
            )
            self._log_applied(change)
            changes.append(change)
        return changes

    def _apply_agent_improvement(
        self,
        learnings: list[Learning],
    ) -> list[AppliedChange]:
        changes: list[AppliedChange] = []
        agents_dir = self.template_path / ".opencode" / "agents"

        for learning in learnings:
            agent_file = agents_dir / f"{learning.source_agent}.md"
            if not agent_file.exists():
                continue

            backup = self._backup_file(agent_file)
            existing = agent_file.read_text(encoding="utf-8")
            addition = (
                f"\n\n### Learned: {learning.title}\n"
                f"> *Harvested from {learning.project_name} "
                f"({learning.timestamp[:10]})*\n\n"
                f"{learning.body}\n"
            )
            agent_file.write_text(existing + addition, encoding="utf-8")

            change = AppliedChange(
                category=learning.category.value,
                title=learning.title,
                target_file=str(agent_file.relative_to(self.template_path)),
                description=f"Agent improvement from {learning.project_name}",
                backup_path=backup,
            )
            self._log_applied(change)
            changes.append(change)
        return changes

    def _apply_error_resolution(
        self,
        learnings: list[Learning],
    ) -> list[AppliedChange]:
        changes: list[AppliedChange] = []
        for learning in learnings:
            if not learning.domain:
                continue
            concepts_dir = self.template_path / ".opencode" / "kb" / learning.domain / "concepts"
            concepts_dir.mkdir(parents=True, exist_ok=True)
            catalog_path = concepts_dir / "error-catalog.md"

            backup = self._backup_file(catalog_path) if catalog_path.exists() else ""

            if catalog_path.exists():
                content = catalog_path.read_text(encoding="utf-8")
            else:
                content = (
                    f"# {learning.domain.title()} Error Catalog\n\n"
                    "Common errors and their resolutions.\n\n"
                )

            content += (
                f"\n## {learning.title}\n\n"
                f"**Error:** {learning.body}\n\n"
                f"**Resolution:** See source — {learning.source_agent}\n\n"
                f"*From: {learning.project_name} ({learning.timestamp[:10]})*\n"
            )
            catalog_path.write_text(content, encoding="utf-8")

            change = AppliedChange(
                category=learning.category.value,
                title=learning.title,
                target_file=str(catalog_path.relative_to(self.template_path)),
                description=f"Error catalog entry from {learning.project_name}",
                backup_path=backup,
            )
            self._log_applied(change)
            changes.append(change)
        return changes

    def _apply_pattern_discovered(
        self,
        learnings: list[Learning],
    ) -> list[AppliedChange]:
        changes: list[AppliedChange] = []
        for learning in learnings:
            if not learning.domain:
                continue
            patterns_dir = self.template_path / ".opencode" / "kb" / learning.domain / "patterns"
            patterns_dir.mkdir(parents=True, exist_ok=True)
            slug = learning.title.lower().replace(" ", "-").replace("/", "-")[:40]
            pattern_path = patterns_dir / f"{slug}.md"

            content = self._generate_kb_article(learning)
            backup = self._backup_file(pattern_path) if pattern_path.exists() else ""

            pattern_path.write_text(content, encoding="utf-8")
            change = AppliedChange(
                category=learning.category.value,
                title=learning.title,
                target_file=str(pattern_path.relative_to(self.template_path)),
                description=f"Pattern from {learning.project_name}",
                backup_path=backup,
            )
            self._log_applied(change)
            changes.append(change)
        return changes

    def apply(self, dry_run: bool = False) -> list[AppliedChange]:
        """Apply all harvested learnings to the template."""
        all_changes: list[AppliedChange] = []
        by_cat: dict[str, list[Learning]] = {}
        for learning in self.load_harvested():
            by_cat.setdefault(learning.category.value, []).append(learning)

        appliers = {
            LearningCategory.KB_INSIGHT.value: self._apply_kb_insight,
            LearningCategory.AGENT_IMPROVEMENT.value: self._apply_agent_improvement,
            LearningCategory.ERROR_RESOLUTION.value: self._apply_error_resolution,
            LearningCategory.PATTERN_DISCOVERED.value: self._apply_pattern_discovered,
        }

        for cat, applier in appliers.items():
            items = by_cat.get(cat, [])
            if not items:
                continue
            if not dry_run:
                changes = applier(items)
                all_changes.extend(changes)
            else:
                for learning in items:
                    all_changes.append(
                        AppliedChange(
                            category=cat,
                            title=learning.title,
                            target_file=f"(dry run) {learning.domain}/{learning.title}",
                            description=f"Would apply from {learning.project_name}",
                        )
                    )
        return all_changes

    # ── Rollback ──────────────────────────────────────────────

    def rollback(self, change_id: str | None = None) -> list[str]:
        """Rollback applied changes. If no ID, rollback the last one."""
        if change_id:
            log_files = [APPLIED_DIR / f"{change_id}.json"]
        else:
            log_files = sorted(APPLIED_DIR.glob("*.json"), reverse=True)[:1]

        restored: list[str] = []
        for log_file in log_files:
            if not log_file.exists():
                continue
            try:
                change = AppliedChange(**json.loads(log_file.read_text(encoding="utf-8")))
                if change.backup_path and Path(change.backup_path).exists():
                    target = self.template_path / change.target_file
                    shutil.copy2(change.backup_path, target)
                    restored.append(change.target_file)
                log_file.unlink()
            except Exception:
                pass
        return restored

    # ── Status ────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        projects = self.load_projects()
        active = [p for p in projects if p.status == "active"]
        harvested = self.load_harvested()
        applied = list(APPLIED_DIR.glob("*.json"))
        return {
            "projects_registered": len(projects),
            "projects_active": len(active),
            "learnings_harvested": len(harvested),
            "improvements_applied": len(applied),
            "analysis": self.analyze(),
        }

    def print_status(self):
        s = self.status()
        print("\n=== Evolve Engine Status ===\n")
        print(f"  Projects registered: {s['projects_registered']}")
        print(f"  Projects active:      {s['projects_active']}")
        print(f"  Learnings harvested:  {s['learnings_harvested']}")
        print(f"  Improvements applied: {s['improvements_applied']}")

        a = s["analysis"]
        if a["by_category"]:
            print("\n  By Category:")
            for cat, count in a["by_category"].items():
                print(f"    {cat}: {count}")
        if a["high_value_items"]:
            print("\n  Top High-Value Learnings:")
            for item in a["high_value_items"][:5]:
                print(f"    [{item['id']}] {item['title']} ({item['category']})")
        print()


evolve_engine = EvolveEngine()
