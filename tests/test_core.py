"""
Comprehensive test suite for LTADE core components.
"""

import json
import os

# ---------------------------------------------------------------------------
# ProjectHarness
# ---------------------------------------------------------------------------
from src.core.harness import ProjectHarness


class TestHarness:
    def test_initialize(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            h = ProjectHarness("test")
            assert h.check_health()["status"] == "OK"
            assert os.path.exists(".harness_state.json")
        finally:
            os.chdir(cwd)

    def test_register_spec(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            h = ProjectHarness("test")
            h.register_spec("my-feature")
            with open(".harness_state.json") as f:
                state = json.load(f)
            assert "my-feature" in state["active_specs"]
        finally:
            os.chdir(cwd)

    def test_set_github(self, tmp_path):
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            h = ProjectHarness("test")
            h.set_github_repo("https://github.com/user/repo")
            with open(".harness_state.json") as f:
                state = json.load(f)
            assert state["github_repo"] == "https://github.com/user/repo"
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# DataQualityValidator
# ---------------------------------------------------------------------------

from src.core.data_quality import DataQualityValidator, QualityCheck


class TestDataQuality:
    def _setup_table(self, validator):
        validator.con.execute("""
            CREATE TABLE test_table AS SELECT * FROM (VALUES
                (1, 'alice', 30, 100.0, '2024-01-01'::date),
                (2, 'bob', 25, 200.0, '2024-01-02'::date),
                (NULL, 'charlie', -5, 300.0, '2099-01-01'::date),
                (4, NULL, 35, -50.0, '2023-12-31'::date),
                (5, 'dave', 30, 150.0, '2024-01-01'::date),
            ) AS t(id, name, age, salary, date_col)
        """)

    def test_not_null(self):
        v = DataQualityValidator()
        self._setup_table(v)
        results = v.check_table("test_table", [QualityCheck(column="id", rule="not_null")])
        assert not results[0].passed
        assert results[0].failed_rows == 1
        v.close()

    def test_unique(self):
        v = DataQualityValidator()
        self._setup_table(v)
        results = v.check_table("test_table", [QualityCheck(column="age", rule="unique")])
        assert not results[0].passed
        v.close()

    def test_positive(self):
        v = DataQualityValidator()
        self._setup_table(v)
        results = v.check_table("test_table", [QualityCheck(column="salary", rule="positive")])
        assert not results[0].passed
        v.close()

    def test_non_negative(self):
        v = DataQualityValidator()
        self._setup_table(v)
        results = v.check_table("test_table", [QualityCheck(column="age", rule="non_negative")])
        assert not results[0].passed
        v.close()

    def test_in_range(self):
        v = DataQualityValidator()
        self._setup_table(v)
        results = v.check_table(
            "test_table",
            [QualityCheck(column="age", rule="in_range", params={"min": 18, "max": 65})],
        )
        assert not results[0].passed
        v.close()

    def test_in_set(self):
        v = DataQualityValidator()
        self._setup_table(v)
        results = v.check_table(
            "test_table",
            [
                QualityCheck(
                    column="name", rule="in_set", params={"values": ["alice", "bob", "dave"]}
                )
            ],
        )
        assert not results[0].passed
        v.close()

    def test_no_future_dates(self):
        v = DataQualityValidator()
        self._setup_table(v)
        results = v.check_table(
            "test_table", [QualityCheck(column="date_col", rule="no_future_dates")]
        )
        assert not results[0].passed
        v.close()

    def test_report(self):
        v = DataQualityValidator()
        self._setup_table(v)
        checks = [
            QualityCheck(column="id", rule="not_null"),
            QualityCheck(column="id", rule="unique"),
        ]
        results = v.check_table("test_table", checks)
        report = v.report(results)
        assert "passed" in report or "failed" in report
        v.close()

    def test_unknown_rule(self):
        v = DataQualityValidator()
        self._setup_table(v)
        results = v.check_table("test_table", [QualityCheck(column="id", rule="nonexistent")])
        assert not results[0].passed
        assert "Unknown rule" in (results[0].error or "")
        v.close()

    def test_all_pass_on_clean(self):
        v = DataQualityValidator()
        v.con.execute("""
            CREATE TABLE clean AS SELECT * FROM (VALUES
                (1, 10.0), (2, 20.0), (3, 30.0)
            ) AS t(id, val)
        """)
        checks = [
            QualityCheck(column="id", rule="not_null"),
            QualityCheck(column="id", rule="unique"),
            QualityCheck(column="val", rule="positive"),
        ]
        results = v.check_table("clean", checks)
        assert all(r.passed for r in results)
        v.close()


# ---------------------------------------------------------------------------
# Medallion Pipeline Integration (requires sample data)
# ---------------------------------------------------------------------------

from src.pipelines.medallion import bronze, silver


class TestMedallion:
    def test_bronze_ingest_csv(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("id,name\n1,alice\n2,bob\n")
        db_path = str(tmp_path / "bronze.duckdb")
        count = bronze.ingest_csv("test_table", str(csv_path), db_path)
        assert count == 2

    def test_bronze_list_tables(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("x\n1\n2\n")
        db_path = str(tmp_path / "bronze.duckdb")
        bronze.ingest_csv("mytable", str(csv_path), db_path)
        tables = bronze.list_bronze_tables(db_path)
        assert "mytable" in tables

    def test_silver_transform(self, tmp_path):
        csv_path = tmp_path / "src.csv"
        csv_path.write_text("id,name\n1,alice\n2,bob\n1,alice\n")
        bronze_db = str(tmp_path / "bronze.duckdb")
        silver_db = str(tmp_path / "silver_out.duckdb")
        bronze.ingest_csv("src", str(csv_path), bronze_db)
        result = silver.bronze_to_silver("src", "dest", db_path=bronze_db, silver_path=silver_db)
        assert result["rows"] == 2
        assert "quality" in result


# ---------------------------------------------------------------------------
# FlowCheck CLI
# ---------------------------------------------------------------------------

from cli import flowcheck


class TestFlowCheck:
    def test_status_no_data(self, capsys):
        flowcheck.cmd_status(None)
        captured = capsys.readouterr()
        assert "FlowCheck" in captured.out


# ---------------------------------------------------------------------------
# Decision Log
# ---------------------------------------------------------------------------

from src.core.decision_log import DecisionLogStore
from src.schemas.decisions import DecisionLog, DecisionStatus


class TestDecisionLog:
    def test_add_and_all(self, tmp_path):
        store = DecisionLogStore(str(tmp_path / "decisions.json"))
        d = DecisionLog(
            id="ADR-001",
            title="Use DuckDB VSS",
            status=DecisionStatus.accepted,
            context="Need zero-infra vector search",
            decision="Use DuckDB VSS extension instead of Qdrant",
            consequences="Simpler setup for templates",
            sdd_phase="design",
            author="test",
        )
        store.add(d)
        all_d = store.all()
        assert len(all_d) == 1
        assert all_d[0].title == "Use DuckDB VSS"

    def test_next_id(self, tmp_path):
        store = DecisionLogStore(str(tmp_path / "decisions.json"))
        d = DecisionLog(
            id=store.next_id(),
            title="Test",
            status=DecisionStatus.accepted,
            context="x",
            decision="y",
            consequences="z",
            sdd_phase="build",
        )
        store.add(d)
        d2 = DecisionLog(
            id=store.next_id(),
            title="Test 2",
            status=DecisionStatus.proposed,
            context="x",
            decision="y",
            consequences="z",
            sdd_phase="design",
        )
        store.add(d2)
        assert d.id == "ADR-001"
        assert d2.id == "ADR-002"

    def test_by_phase(self, tmp_path):
        store = DecisionLogStore(str(tmp_path / "decisions.json"))
        for i, phase in enumerate(["brainstorm", "define", "design"]):
            store.add(
                DecisionLog(
                    id=f"ADR-{i:03d}",
                    title=f"Phase {phase}",
                    status=DecisionStatus.accepted,
                    context="x",
                    decision="y",
                    consequences="z",
                    sdd_phase=phase,
                )
            )
        assert len(store.by_phase("design")) == 1
        assert len(store.by_phase("build")) == 0

    def test_status_summary(self, tmp_path):
        store = DecisionLogStore(str(tmp_path / "decisions.json"))
        assert store.status_summary()["total"] == 0
        store.add(
            DecisionLog(
                id="ADR-001",
                title="T1",
                status=DecisionStatus.accepted,
                context="x",
                decision="y",
                consequences="z",
                sdd_phase="build",
            )
        )
        store.add(
            DecisionLog(
                id="ADR-002",
                title="T2",
                status=DecisionStatus.proposed,
                context="x",
                decision="y",
                consequences="z",
                sdd_phase="build",
            )
        )
        summary = store.status_summary()
        assert summary["total"] == 2
        assert summary["accepted"] == 1
        assert summary["proposed"] == 1


# ---------------------------------------------------------------------------
# RAG (DuckDB VSS)
# ---------------------------------------------------------------------------


class TestRag:
    def test_chunk_text(self):
        from src.rag.ingest import chunk_text

        text = "a" * 2500
        chunks = chunk_text(text, chunk_size=1000, overlap=100)
        assert len(chunks) == 3
        assert all(len(c) <= 1000 for c in chunks)

    def test_chunk_small_text(self):
        from src.rag.ingest import chunk_text

        chunks = chunk_text("hello world", chunk_size=1000, overlap=100)
        assert len(chunks) == 1
        assert chunks[0] == "hello world"


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

from src.core.llm import LLMClient


class TestLLMClient:
    def test_init(self):
        client = LLMClient()
        assert client.nim_url is not None
        assert client.default_model is not None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

from src.schemas.messages import AgentMessage
from src.schemas.state import AgentState, ProjectState, TaskState, WorkflowState
from src.schemas.tasks import Task, TaskResult, WorkflowDefinition


class TestSchemas:
    def test_task(self):
        t = Task(task_id="t1", task_type="run_query", agent_type="data-pipeline")
        assert t.task_id == "t1"

    def test_task_result(self):
        r = TaskResult(task_id="t1", status="completed", output={"rows": 10})
        assert r.status == "completed"

    def test_workflow_definition(self):
        w = WorkflowDefinition(workflow_id="w1", name="test", tasks=[])
        assert w.name == "test"

    def test_agent_message(self):
        m = AgentMessage(msg_id="m1", msg_type="request", topic="test", sender="agent1")
        assert m.sender == "agent1"

    def test_agent_state(self):
        s = AgentState(agent_id="a1", agent_type="orchestrator")
        assert s.status == "idle"

    def test_task_state_defaults(self):
        s = TaskState(task_id="t1", workflow_id="w1", agent_type="analytics")
        assert s.status == "pending"
        assert s.max_retries == 3

    def test_workflow_state(self):
        s = WorkflowState(workflow_id="w1", name="test")
        assert s.status == "pending"

    def test_project_state(self):
        s = ProjectState(project_name="test")
        assert s.active_workflows == []
