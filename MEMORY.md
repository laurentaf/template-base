# Project Memory & Handoff

## Current Objective
Make template-base a zero-config boot project with confidence-driven agents, consensus workflows, auto-doc/auto-git, and a global self-evolve system.

## Accomplished
- Replaced all 9 hardcoded `E:\projects\template-base` paths with auto-detect/env var (`LTADE_TEMPLATE_PATH` + git root fallback)
- Fixed Dockerfile Python 3.12 → 3.11, added non-root user + HEALTHCHECK
- Added missing `data/__init__.py` + `data/generators/__init__.py`
- Removed hardcoded DB password from config.py default + bootstrapper.py default
- Fixed SQL injection in analytics_agent, data_pipeline_agent, reviewer_agent (identifier quoting + parameterized queries)
- Rewrote `chat_async()` as truly async with `httpx.AsyncClient`
- Added retry/backoff (exponential, 3 attempts) for 429/5xx in LLMClient
- Wired LLM into code_gen_agent (dbt models, pipelines, SQL generation now LLM-powered)
- Made gold.py dynamic — discovers silver tables from DuckDB catalog
- Added OTel atexit shutdown in telemetry.py
- Added agent PID tracking/cleanup to AgentManager
- Added healthchecks to all docker-compose agent services
- Removed hardcoded DB password from docker-compose.yml
- Added Makefile (lint/test/format/docker/pipeline/health/check/init/clean)
- Added bash `init_project.sh` + fixed PS1 `init_project.ps1` (auto-detect template path)
- Completed `.env.example` with all 30+ config keys
- Added `tests/conftest.py` with shared fixtures
- Created confidence engine, consensus engine, bootstrapper, planner, auto_doc, auto_git
- Created learning emitter + evolve engine + harvest daemon
- Created KB domain structure (18 domains, 55 files)
- Fixed gold.py inline SQL, task_queue.py nack(), telemetry.py import crash
- Fixed main.py Typer 0.25+ compatibility (`app.add_typer()`)

## Blocked / Pending
- (none currently)

## Next Steps (For the Next Agent)
1. Run full `ruff check + ruff format + pytest` to verify all changes
2. Consider adding integration tests for agents (analytics, data-pipeline, code-gen)
3. Consider adding type checking (`mypy` or `pyright`) to CI
4. Consider adding pre-commit hooks

## Key Decisions & Rationale
- Global watcher architecture: separate `~/.ltade/evolve/` service, projects are passive
- 6 learning categories → evolve targets mapping (kb_insight→KB, agent_improvement→agent .md, etc.)
- `EVOLVE_AUTO_APPLY=false` by default — explicit user action required
- LLM generates KB articles from raw learnings during apply
- All applies create backups in `~/.ltade/evolve/rollback/` for rollback
- `LTADE_TEMPLATE_PATH` env var + auto-detect via `git rev-parse --show-toplevel` or `Path(__file__)` fallback
- SQL identifiers validated via regex + quoted; file paths parameterized
- `chat_async()` uses `httpx.AsyncClient` — no event loop blocking
- Retry with exponential backoff (2^attempt seconds) for 429/5xx

---
*Last update by: opencode at 2026-05-24*
