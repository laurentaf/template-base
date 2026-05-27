# AGENT_SYSTEM.md — Mandatory Operating Contract

> **This file is NON-NEGOTIABLE.** Every agent MUST read it completely before any action.
> **Single source of truth** — all operational rules, project context, and protocols live here.

---

## 1. Execution Rules (MANDATORY)

| # | Rule | Enforcement |
|---|------|-------------|
| 1 | Read `AGENT_SYSTEM.md` completely | Bootstrap check + agent frontmatter |
| 2 | Follow SDD workflow (no code without specs) | Pre-commit hook + confidence gate |
| 3 | Register decisions in decision log | `ltade decision add` required before ADR |
| 4 | Run evals/tests before finalizing | CI gate + `make check` |
| 5 | Update `MEMORY.md` after every task | Agent post-task hook |
| 6 | Confidence gate — research if below threshold | ConfidenceEngine auto-evaluation |

**Violation = STOP.** Do not proceed. Report the gap and fix it.

---

## 2. Project Identity

- **Name:** {{PROJECT_NAME}}
- **Template:** LTADE template-base v0.1
- **Stack:** Python 3.11, uv, DuckDB (VSS), Postgres, Redis, Prefect, LangGraph
- **Orchestration:** Prefect, LangGraph

### Infrastructure Availability

| Service | URL | Status Check |
|---------|-----|-------------|
| PostgreSQL | localhost:5433 | `docker ps` |
| Qdrant | localhost:6333 | `curl localhost:6333/healthz` |
| Phoenix | localhost:6006 | Web UI |
| Prefect | localhost:4200 | Web UI |
| Redis | localhost:6379 | `redis-cli ping` |
| NIM Bridge | localhost:8081 | `/v1/chat/completions` |
| MinIO | localhost:9000 | Web UI :9001 |

### Execution Tier

- **Current tier:** {{EXECUTION_TIER}} (development / staging / production)
- Development: Full access, test data only
- Staging: Read-only prod-like data, no destructive operations
- Production: Read-only queries, no DDL, no DML without explicit approval

---

## 3. Grounding Protocol

Before taking any action, load and verify:

1. **Read `AGENT_SYSTEM.md`** — This contract (you are here)
2. **Read `MEMORY.md`** — Current session state, blockers, next steps
3. **Read `.opencode/context/registry.yaml`** — Find active project context
4. **Read `spec/todo.md`** — Active task plan (if exists)
5. **Read `spec/design.md`** — Architecture design (if exists)

**KB-first cognition:** Check `docs/knowledge_base.md` and `.opencode/kb/`
before writing new code. Every response must be evidence-scored (cite source).
No guessing — if context is missing, ask the user.

---

## 4. Project Structure (REQUIRED)

Every project spawned from this template MUST have:

```
<project-root>/
├── AGENT_SYSTEM.md          # ← THIS FILE (single source of truth)
├── GROUNDING.md             # Redirect → AGENT_SYSTEM.md (backward compat)
├── MEMORY.md                # Agent handoff state
├── spec/
│   ├── design.md            # Architecture spec (write FIRST)
│   ├── todo.md              # Active task tracker
│   └── lessons.md           # Lessons learned (append-only)
├── evals/                   # Evaluation scripts and results
├── decisions/               # Architecture Decision Records
├── .opencode/               # Agent configs, skills, KB
├── src/                     # Source code
├── tests/                   # pytest suite
└── scripts/                 # Automation
```

Bootstrap (`ltade init`) verifies all required dirs/files exist.
If `AGENT_SYSTEM.md` is missing at root, bootstrap FAILS.

---

## 5. SDD Workflow with Quality Gates

Every feature follows 5 phases. Each has a mandatory quality gate.

### Phase 0 — Brainstorm
- **Location:** `spec/brainstorm/{feature}/BRAINSTORM.md`
- **Gate:** 3+ approaches, 3+ questions, YAGNI filter, success criteria

### Phase 1 — Define
- **Location:** `spec/define/{feature}/DEFINE.md`
- **Gate:** Clarity score >= 12/15

### Phase 2 — Design
- **Location:** `spec/design/{feature}/DESIGN.md`
- **Gate:** Complete file manifest, ADRs, schema, data flow

### Phase 3 — Build
- **Location:** Code in `src/` + `spec/build/{feature}/BUILD_REPORT.md`
- **Gate:** All tests pass, Ruff clean, no hardcoded secrets

### Phase 4 — Ship
- **Location:** `spec/archive/{feature}/SHIPPED.md`
- **Gate:** Validation score >= 90, lessons captured

### Cross-phase: Iterate
When requirements change, update the relevant phase document and
cascade-check downstream. Re-run gates on affected phases.

---

## 6. Confidence Protocol

Every substantive action must pass through confidence validation.

### Task Thresholds

| Category | Threshold | Action If Below |
|----------|-----------|-----------------|
| CRITICAL (security, auth, secrets) | 0.98 | REFUSE + explain |
| IMPORTANT (architecture, breaking changes) | 0.95 | ASK user first |
| STANDARD (new features, refactoring) | 0.90 | RESEARCH then proceed |
| ADVISORY (docs, formatting) | 0.80 | PROCEED freely |

### Decision Flow

1. CLASSIFY → What type of task? What threshold?
2. LOAD → Read KB patterns from `.opencode/kb/{domain}/`
3. VALIDATE → Query MCP if KB insufficient
4. CALCULATE → Base score + modifiers = final confidence
5. DECIDE → confidence >= threshold? Execute / Research / Ask / Refuse

### Agreement Matrix

| | MCP AGREES | MCP DISAGREES | MCP SILENT |
|---|---|---|---|
| **KB HAS PATTERN** | HIGH: 0.95 → Execute | CONFLICT: 0.50 → Investigate | MEDIUM: 0.75 → Proceed |
| **KB SILENT** | MCP-ONLY: 0.85 → Proceed | N/A | LOW: 0.50 → Research |

### Research Protocol (when below threshold)

1. Check KB domains (`.opencode/kb/`)
2. Query MCP servers for validation
3. Search internet if still uncertain
4. Max 3 research rounds before asking user
5. **Always present final plan to user before executing**
6. Only auto-execute without asking if confidence >= 98%

---

## 7. Code Quality Rules

- Pydantic for ALL data models and configs
- Google-style docstrings on all public functions
- Imports grouped: standard lib → third party → local
- Ruff formatting (`uv run ruff format .`) before declaring done
- Tests alongside or before implementation
- No hardcoded secrets — all credentials via env vars
- SQL injection prevention — use identifier quoting + parameterized queries
- Check Phoenix traces at `http://localhost:6006` when debugging

---

## 8. Self-Evolve Protocol

Every project auto-emits learnings to `.learnings/` on task completion.
The global EvolveEngine harvests these and improves the template.

### Learning Loop

```
Project A discovers pattern
→ .learnings/ emits learning (auto on every task)
→ Global EvolveEngine harvests periodically
→ Template KB/agents/config improve
→ Project B starts with better defaults
```

### Learning Categories

| Category | Evolve Target | Example |
|---|---|---|
| `kb_insight` | `.opencode/kb/{domain}/concepts/` | New DuckDB pattern |
| `agent_improvement` | `.opencode/agents/*.md` | Reviewer learns SQL injection check |
| `config_tuning` | `src/core/config.py` defaults | Better Redis URL pattern |
| `pattern_discovered` | `.opencode/kb/{domain}/patterns/` | Reusable medallion pattern |
| `error_resolution` | `.opencode/kb/{domain}/concepts/error-catalog.md` | Telemetry crash fix |
| `workflow_optimization` | Orchestrator/consensus defaults | Parallel dispatch tuning |

### Commands

- `ltade evolve discover` — Find projects with .learnings/
- `ltade evolve harvest` — Pull learnings from all projects
- `ltade evolve analyze` — Rank learnings by value
- `ltade evolve apply` — Write improvements to template
- `ltade evolve rollback` — Undo last apply
- `ltade evolve status` — Show evolve state

### Rules

- Only **active** (in-progress) projects emit learnings
- Learnings require confidence >= 0.7 to be auto-applied
- All applies are backed up for rollback
- `EVOLVE_AUTO_APPLY=false` by default — user must explicitly run `ltade evolve apply`

---

## 9. Multi-Agent Protocol

### Agent Types

| Agent | Capabilities | Start Command |
|-------|-------------|---------------|
| `orchestrator` | DAG decomposition, dispatch, aggregation | `uv run python -m src.agents.orchestrator` |
| `data-pipeline` | ETL, queries, ingestion, validation | `uv run python -m src.agents.data_pipeline_agent` |
| `analytics` | Aggregations, anomaly detection, reports | `uv run python -m src.agents.analytics_agent` |
| `code-gen` | dbt models, pipeline code, SQL | `uv run python -m src.agents.code_gen_agent` |
| `reviewer` | Code review, schema validation, security | `uv run python -m src.agents.reviewer_agent` |

### Consensus Patterns

| Pattern | When | How |
|---------|------|-----|
| CONSENSUS | Architecture decisions | Multiple agents vote, majority wins |
| PARALLEL | Batch validation | Fan-out to N agents, gather all |
| HIERARCHICAL | Complex multi-phase | Orchestrator delegates to sub-orchestrators |
| SEQUENTIAL | Linear pipelines | Chain building on previous output |

---

## 10. Verification Before Done

Every task must pass these checks before being considered complete:

- [ ] `uv run ruff check src/ tests/` — clean
- [ ] `uv run ruff format --check src/ tests/` — clean
- [ ] `uv run pytest tests/ -v` — all pass
- [ ] No hardcoded secrets or paths
- [ ] MEMORY.md updated with current state
- [ ] Decision log updated if architectural choice was made
- [ ] Lessons captured if something was learned

---

*This document is the single source of truth for agent behavior. Enforced at bootstrap, pre-commit, CI, and runtime.*
