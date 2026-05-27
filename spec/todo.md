# Task Plan

## Current Sprint
- [x] P0: Replace all 9 hardcoded `E:\projects\template-base` paths with auto-detect/env var
- [x] P0: Fix Dockerfile Python 3.12 → 3.11
- [x] P0: Add missing `data/__init__.py` and `data/generators/__init__.py`
- [x] P1: Remove hardcoded DB password from config.py default + bootstrapper + docker-compose
- [x] P1: Fix SQL injection in analytics_agent, data_pipeline_agent, reviewer_agent
- [x] P1: Make `chat_async()` truly async with `httpx.AsyncClient`
- [x] P2: Wire LLM into code_gen_agent (replace SELECT 1 stubs)
- [x] P2: Make gold.py dynamic (discover silver tables from catalog)
- [x] P2: Add retry/backoff to LLM client for 429/5xx
- [x] P3: Add Makefile with lint/test/format/docker/pipeline/health targets
- [x] P3: Add bash init_project.sh
- [x] P3: Complete `.env.example` with all keys
- [x] P3: Add `tests/conftest.py` with shared fixtures
- [x] P4: Add non-root user + HEALTHCHECK to Dockerfile
- [x] P4: Add healthchecks to docker-compose agent services
- [x] P4: Add OTel shutdown via atexit in telemetry.py
- [x] P4: Add agent PID cleanup to AgentManager
- [x] P4: Fill stub content in MEMORY.md and spec/todo.md

## Backlog
- [ ] Run full ruff lint + pytest to verify all changes pass
- [ ] Add integration tests for agents (analytics, data-pipeline, code-gen)
- [ ] Add type checking (mypy/pyright) to CI
- [ ] Add pre-commit hooks config
- [ ] Add CI/CD pipeline (GitHub Actions)
- [ ] Wire WorkflowState naming conflict (schemas/state.py vs orchestrator TypedDict)
