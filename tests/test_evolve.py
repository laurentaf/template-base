"""End-to-end tests for the Evolve Engine.

Full lifecycle: register → emit → harvest → analyze → apply → rollback
Uses temp directories so no real project state is touched.
"""

from pathlib import Path

import pytest

from src.core.evolve_engine import EvolveEngine
from src.core.learnings import LearningCategory, LearningEmitter


@pytest.fixture
def evolve_env(tmp_path, monkeypatch):
    """Set up isolated evolve environment with temp dirs."""
    evolve_dir = tmp_path / ".ltade" / "evolve"
    evolve_dir.mkdir(parents=True)

    learnings_dir = evolve_dir / "learnings"
    applied_dir = evolve_dir / "applied"
    rollback_dir = evolve_dir / "rollback"
    projects_file = evolve_dir / "projects.json"

    for d in (learnings_dir, applied_dir, rollback_dir):
        d.mkdir(parents=True)

    template_dir = tmp_path / "template-base"
    template_dir.mkdir()
    kb_dir = template_dir / ".opencode" / "kb"
    agents_dir = template_dir / ".opencode" / "agents"
    kb_dir.mkdir(parents=True)
    agents_dir.mkdir(parents=True)

    monkeypatch.setattr("src.core.evolve_engine.EVOLVE_DIR", evolve_dir)
    monkeypatch.setattr("src.core.evolve_engine.PROJECTS_FILE", projects_file)
    monkeypatch.setattr("src.core.evolve_engine.LEARNINGS_DIR", learnings_dir)
    monkeypatch.setattr("src.core.evolve_engine.APPLIED_DIR", applied_dir)
    monkeypatch.setattr("src.core.evolve_engine.ROLLBACK_DIR", rollback_dir)

    engine = EvolveEngine(template_path=str(template_dir))
    engine._ensure_dirs()

    return {
        "engine": engine,
        "evolve_dir": evolve_dir,
        "learnings_dir": learnings_dir,
        "applied_dir": applied_dir,
        "rollback_dir": rollback_dir,
        "projects_file": projects_file,
        "template_dir": template_dir,
        "kb_dir": kb_dir,
        "agents_dir": agents_dir,
    }


@pytest.fixture
def project_dir(tmp_path):
    """Create a fake project with .learnings/ capability."""
    proj = tmp_path / "my-project"
    proj.mkdir()
    return proj


class TestEvolveRegister:
    def test_register_new_project(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        entry = engine.register_project(str(project_dir), name="my-project")
        assert entry.name == "my-project"
        assert entry.status == "active"
        assert entry.path == str(project_dir.resolve())

    def test_register_idempotent(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        e1 = engine.register_project(str(project_dir), name="my-project")
        e2 = engine.register_project(str(project_dir), name="my-project")
        assert e1.path == e2.path
        projects = engine.load_projects()
        assert len(projects) == 1

    def test_load_projects_empty(self, evolve_env):
        engine = evolve_env["engine"]
        assert engine.load_projects() == []

    def test_save_and_load_roundtrip(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")
        loaded = engine.load_projects()
        assert len(loaded) == 1
        assert loaded[0].name == "test-proj"


class TestEvolveEmitAndHarvest:
    def test_emit_and_harvest(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.KB_INSIGHT,
            title="DuckDB VSS needs float32",
            body="Embeddings must be cast to float32 for DuckDB VSS index",
            domain="duckdb",
            confidence=0.9,
            project_name="test-proj",
            source_agent="analytics",
        )

        learnings = engine.harvest(str(project_dir))
        assert len(learnings) == 1
        assert learnings[0].title == "DuckDB VSS needs float32"
        assert learnings[0].category == LearningCategory.KB_INSIGHT

    def test_harvest_increments_learning_count(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.PATTERN_DISCOVERED,
            title="Date partitioning speeds up queries",
            body="Partitioning by date in silver layer gives 3x speedup",
            domain="medallion",
            confidence=0.85,
            project_name="test-proj",
            source_agent="data-pipeline",
        )

        engine.harvest(str(project_dir))
        projects = engine.load_projects()
        assert projects[0].learning_count >= 1

    def test_harvest_all_skips_inactive(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="inactive-proj")

        projects = engine.load_projects()
        for p in projects:
            if p.name == "inactive-proj":
                p.status = "done"
        engine.save_projects(projects)

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.KB_INSIGHT,
            title="Test",
            body="Body",
            domain="python",
            confidence=0.5,
            project_name="inactive-proj",
            source_agent="orchestrator",
        )

        results = engine.harvest_all()
        assert "inactive-proj" not in results

    def test_harvest_all_includes_active(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="active-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.ERROR_RESOLUTION,
            title="Import crash on telemetry",
            body="Defer config import to avoid circular dependency",
            domain="python",
            confidence=0.7,
            project_name="active-proj",
            source_agent="orchestrator",
        )

        results = engine.harvest_all()
        assert "active-proj" in results
        assert len(results["active-proj"]) == 1

    def test_load_harvested_filters_by_category(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.KB_INSIGHT,
            title="KB item",
            body="body",
            domain="duckdb",
            confidence=0.8,
            project_name="test-proj",
            source_agent="analytics",
        )
        emitter.emit(
            category=LearningCategory.ERROR_RESOLUTION,
            title="Error item",
            body="body",
            domain="python",
            confidence=0.6,
            project_name="test-proj",
            source_agent="orchestrator",
        )

        engine.harvest(str(project_dir))
        kb_items = engine.load_harvested(category="kb_insight")
        assert len(kb_items) == 1
        assert kb_items[0].category == LearningCategory.KB_INSIGHT


class TestEvolveAnalyze:
    def test_analyze_empty(self, evolve_env):
        engine = evolve_env["engine"]
        result = engine.analyze()
        assert result["total"] == 0
        assert result["high_value"] == 0

    def test_analyze_with_learnings(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        for i in range(3):
            emitter.emit(
                category=LearningCategory.KB_INSIGHT,
                title=f"Insight {i}",
                body=f"Body {i}",
                domain="duckdb",
                confidence=0.8,
                project_name="test-proj",
                source_agent="analytics",
            )
        emitter.emit(
            category=LearningCategory.ERROR_RESOLUTION,
            title="Low conf error",
            body="body",
            domain="python",
            confidence=0.3,
            project_name="test-proj",
            source_agent="orchestrator",
        )

        engine.harvest(str(project_dir))
        result = engine.analyze()
        assert result["total"] == 4
        assert result["by_category"]["kb_insight"] == 3
        assert result["by_category"]["error_resolution"] == 1
        assert result["high_value"] >= 3

    def test_analyze_high_value_includes_error_resolution(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.ERROR_RESOLUTION,
            title="Critical bug fix",
            body="Fix null pointer in gold layer",
            domain="medallion",
            confidence=0.3,
            project_name="test-proj",
            source_agent="data-pipeline",
        )

        engine.harvest(str(project_dir))
        result = engine.analyze()
        assert result["high_value"] == 1
        assert result["high_value_items"][0]["title"] == "Critical bug fix"


class TestEvolveApply:
    def test_apply_kb_insight(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.KB_INSIGHT,
            title="DuckDB VSS needs float32",
            body="Cast embeddings to float32 before creating VSS index",
            domain="duckdb",
            confidence=0.9,
            project_name="test-proj",
            source_agent="analytics",
        )

        engine.harvest(str(project_dir))

        changes = engine.apply()
        assert len(changes) >= 1
        assert changes[0].category == "kb_insight"

        concepts_dir = evolve_env["kb_dir"] / "duckdb" / "concepts"
        assert concepts_dir.exists()
        articles = list(concepts_dir.glob("*.md"))
        assert len(articles) >= 1

    def test_apply_error_resolution(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.ERROR_RESOLUTION,
            title="Telemetry import crash",
            body="Defer config import to avoid circular dependency at module level",
            domain="python",
            confidence=0.7,
            project_name="test-proj",
            source_agent="orchestrator",
        )

        engine.harvest(str(project_dir))

        changes = engine.apply()
        error_changes = [c for c in changes if c.category == "error_resolution"]
        assert len(error_changes) >= 1

        concepts_dir = evolve_env["kb_dir"] / "python" / "concepts"
        catalog = concepts_dir / "error-catalog.md"
        assert catalog.exists()
        content = catalog.read_text(encoding="utf-8")
        assert "Telemetry import crash" in content

    def test_apply_agent_improvement(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        agent_file = evolve_env["agents_dir"] / "analytics.md"
        agent_file.write_text("# Analytics Agent\n\nHandles queries.\n")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.AGENT_IMPROVEMENT,
            title="Check SQL injection in queries",
            body="Always parameterize user-provided query fragments",
            domain="duckdb",
            confidence=0.85,
            project_name="test-proj",
            source_agent="analytics",
        )

        engine.harvest(str(project_dir))
        changes = engine.apply()
        agent_changes = [c for c in changes if c.category == "agent_improvement"]
        assert len(agent_changes) >= 1

        updated = agent_file.read_text(encoding="utf-8")
        assert "Check SQL injection" in updated

    def test_apply_pattern_discovered(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.PATTERN_DISCOVERED,
            title="Date partitioning speeds up queries",
            body="Partition silver tables by date for 3x query speedup",
            domain="medallion",
            confidence=0.85,
            project_name="test-proj",
            source_agent="data-pipeline",
        )

        engine.harvest(str(project_dir))
        changes = engine.apply()
        pattern_changes = [c for c in changes if c.category == "pattern_discovered"]
        assert len(pattern_changes) >= 1

        patterns_dir = evolve_env["kb_dir"] / "medallion" / "patterns"
        assert patterns_dir.exists()

    def test_apply_dry_run(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.KB_INSIGHT,
            title="Dry run test",
            body="body",
            domain="duckdb",
            confidence=0.8,
            project_name="test-proj",
            source_agent="analytics",
        )

        engine.harvest(str(project_dir))
        changes = engine.apply(dry_run=True)
        assert len(changes) >= 1
        assert "(dry run)" in changes[0].target_file

        applied_files = list(evolve_env["applied_dir"].glob("*.json"))
        assert len(applied_files) == 0

    def test_apply_creates_backup(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        agent_file = evolve_env["agents_dir"] / "analytics.md"
        agent_file.write_text("original content\n")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.AGENT_IMPROVEMENT,
            title="New improvement",
            body="body text",
            domain="duckdb",
            confidence=0.8,
            project_name="test-proj",
            source_agent="analytics",
        )

        engine.harvest(str(project_dir))
        changes = engine.apply()

        backup_exists = any(
            c.backup_path and Path(c.backup_path).exists() for c in changes
        )
        assert backup_exists


class TestEvolveRollback:
    def test_rollback_last(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        agent_file = evolve_env["agents_dir"] / "analytics.md"
        original = "original content\n"
        agent_file.write_text(original)

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.AGENT_IMPROVEMENT,
            title="Improvement to rollback",
            body="body text",
            domain="duckdb",
            confidence=0.8,
            project_name="test-proj",
            source_agent="analytics",
        )

        engine.harvest(str(project_dir))
        engine.apply()

        restored = engine.rollback()
        assert len(restored) >= 1
        assert agent_file.read_text(encoding="utf-8") == original

    def test_rollback_by_id(self, evolve_env, project_dir):
        engine = evolve_env["engine"]
        engine.register_project(str(project_dir), name="test-proj")

        agent_file = evolve_env["agents_dir"] / "analytics.md"
        agent_file.write_text("original\n")

        emitter = LearningEmitter(project_root=str(project_dir))
        emitter.emit(
            category=LearningCategory.AGENT_IMPROVEMENT,
            title="Targeted rollback item",
            body="body",
            domain="duckdb",
            confidence=0.8,
            project_name="test-proj",
            source_agent="analytics",
        )

        engine.harvest(str(project_dir))
        changes = engine.apply()
        assert len(changes) >= 1

        restored = engine.rollback(change_id=changes[0].id)
        assert len(restored) >= 1

    def test_rollback_nothing_when_empty(self, evolve_env):
        engine = evolve_env["engine"]
        restored = engine.rollback()
        assert restored == []


class TestEvolveFullLifecycle:
    def test_register_emit_harvest_analyze_apply_rollback(self, evolve_env, project_dir):
        engine = evolve_env["engine"]

        agent_file = evolve_env["agents_dir"] / "analytics.md"
        original_content = "# Analytics Agent\n\nHandles queries.\n"
        agent_file.write_text(original_content)

        entry = engine.register_project(str(project_dir), name="lifecycle-proj")
        assert entry.name == "lifecycle-proj"
        assert entry.status == "active"

        emitter = LearningEmitter(project_root=str(project_dir))

        emitter.emit(
            category=LearningCategory.KB_INSIGHT,
            title="DuckDB float32 for VSS",
            body="Cast embeddings to float32 before VSS index creation",
            domain="duckdb",
            confidence=0.9,
            project_name="lifecycle-proj",
            source_agent="analytics",
        )
        emitter.emit(
            category=LearningCategory.AGENT_IMPROVEMENT,
            title="Parameterize SQL inputs",
            body="Always parameterize user-provided SQL fragments",
            domain="duckdb",
            confidence=0.85,
            project_name="lifecycle-proj",
            source_agent="analytics",
        )
        emitter.emit(
            category=LearningCategory.ERROR_RESOLUTION,
            title="Telemetry import crash",
            body="Defer config import in telemetry.py",
            domain="python",
            confidence=0.7,
            project_name="lifecycle-proj",
            source_agent="orchestrator",
        )

        learnings = engine.harvest(str(project_dir))
        assert len(learnings) == 3

        analysis = engine.analyze()
        assert analysis["total"] == 3
        assert analysis["high_value"] >= 2

        changes = engine.apply()
        assert len(changes) >= 2

        kb_articles = list((evolve_env["kb_dir"] / "duckdb" / "concepts").glob("*.md"))
        assert len(kb_articles) >= 1

        updated_agent = agent_file.read_text(encoding="utf-8")
        assert "Parameterize SQL inputs" in updated_agent

        error_catalog = evolve_env["kb_dir"] / "python" / "concepts" / "error-catalog.md"
        assert error_catalog.exists()
        assert "Telemetry import crash" in error_catalog.read_text(encoding="utf-8")

        applied_files = list(evolve_env["applied_dir"].glob("*.json"))
        for _ in range(len(applied_files)):
            engine.rollback()

        assert agent_file.read_text(encoding="utf-8") == original_content

        status = engine.status()
        assert status["projects_registered"] == 1
        assert status["projects_active"] == 1
        assert status["learnings_harvested"] == 3


class TestEmitFromTaskResult:
    def test_emit_from_error_result(self, project_dir):
        result = LearningEmitter.emit_from_task_result(
            task_type="run_query",
            task_result={"error": "Connection refused to Redis"},
            agent_type="data-pipeline",
            project_name="test-proj",
            project_root=str(project_dir),
        )
        assert result is not None
        assert result.category == LearningCategory.ERROR_RESOLUTION
        assert result.confidence == 0.3

    def test_emit_from_successful_result(self, project_dir):
        result = LearningEmitter.emit_from_task_result(
            task_type="run_query",
            task_result={"rows": 150, "table": "silver.orders"},
            agent_type="data-pipeline",
            project_name="test-proj",
            project_root=str(project_dir),
        )
        assert result is not None
        assert result.category == LearningCategory.PATTERN_DISCOVERED
        assert result.confidence == 0.8

    def test_emit_skips_unknown_task_type(self, project_dir):
        result = LearningEmitter.emit_from_task_result(
            task_type="unknown_type",
            task_result={"some": "data"},
            agent_type="analytics",
            project_name="test-proj",
            project_root=str(project_dir),
        )
        assert result is None


class TestDiscoverProjects:
    def test_discover_finds_project_with_learnings(self, evolve_env, tmp_path):
        engine = evolve_env["engine"]

        search_dir = tmp_path / "projects"
        search_dir.mkdir()
        proj = search_dir / "discovered-proj"
        proj.mkdir()
        (proj / ".learnings").mkdir()

        monkeypatch_search = [
            search_dir,
        ]

        def patched_discover():
            known = {p.path for p in engine.load_projects()}
            for search in monkeypatch_search:
                if not search.exists():
                    continue
                for child in search.iterdir():
                    if child.is_dir() and (child / ".learnings").exists():
                        resolved = str(child.resolve())
                        if resolved not in known:
                            engine.register_project(resolved)
            return engine.load_projects()

        engine.discover_projects = patched_discover

        projects = engine.discover_projects()
        paths = [p.path for p in projects]
        assert str(proj.resolve()) in paths
