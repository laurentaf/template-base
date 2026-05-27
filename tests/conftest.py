import pytest


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LTADE_TEMPLATE_PATH", str(tmp_path / "template"))
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("NVIDIA_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")


@pytest.fixture
def tmp_project(tmp_path):
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "src" / "__init__.py").write_text("")
    return project_dir


@pytest.fixture
def sample_duckdb(tmp_path):
    import duckdb

    db_path = str(tmp_path / "test.duckdb")
    con = duckdb.connect(db_path)
    con.execute(
        "CREATE TABLE test_data AS SELECT * FROM (VALUES "
        "(1, 'alice', 30), (2, 'bob', 25), (3, 'charlie', 35)) "
        "AS t(id, name, age)"
    )
    con.close()
    return db_path
