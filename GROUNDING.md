# Grounding Protocol — Mandatory Context

This document defines the mandatory context that ALL agents must load before
taking any action. Every agent response must be grounded in this context.

## 1. Project Identity
- **Name:** ai-data-project
- **Template:** LTADE template-base v0.1
- **Stack:** Python 3.11, uv, DuckDB (VSS), Postgres, Redis, Prefect, LangGraph
- **Orchestration:** Prefect, LangGraph

## 2. Active Documents (READ THESE FIRST)
| Document | Purpose | Required |
|----------|---------|----------|
| `GROUNDING.md` | This file — mandatory context | ✅ Always |
| `.opencode/context/default/knowledge.md` | Project knowledge context | ✅ Always |
| `MEMORY.md` | Current session state, blockers, next steps | ✅ Always |
| `spec/design.md` | Architecture design (if exists) | ⚠️ If present |
| `spec/todo.md` | Active task plan | ✅ If present |

## 3. Grounding Rules
1. **KB-first** — Check `.opencode/context/` and `docs/knowledge_base.md` before external sources
2. **Evidence-scored** — Every response must cite its source (file + line when possible)
3. **No guessing** — If context is missing, ask the user. Do not fabricate.
4. **Gate-aware** — Never start a phase without the previous phase's gate passing
5. **Handoff** — Update `MEMORY.md` after EVERY task before exiting

## 4. Infrastructure Availability
| Service | URL | Status Check |
|---------|-----|-------------|
| PostgreSQL | localhost:5433 | `docker ps` |
| Qdrant | localhost:6333 | `curl localhost:6333/healthz` |
| Phoenix | localhost:6006 | Web UI |
| Prefect | localhost:4200 | Web UI |
| Redis | localhost:6379 | `redis-cli ping` |
| NIM Bridge | localhost:8081 | `/v1/chat/completions` |
| MinIO | localhost:9000 | Web UI :9001 |

## 5. Execution Tier
- **Current tier:** development (development / staging / production)
- **Tier rules:**
  - Development: Full access, test data only
  - Staging: Read-only prod-like data, no destructive operations
  - Production: Read-only queries, no DDL, no DML without explicit approval

## 6. Confidence Protocol

All agents MUST evaluate confidence before executing substantive tasks:

1. Classify task category (CRITICAL/IMPORTANT/STANDARD/ADVISORY)
2. Calculate confidence using Agreement Matrix
3. If below threshold: research (KB → MCP → internet) up to 3 rounds
4. If still below: ask user with findings
5. Always present plan for user approval before executing
6. Only auto-execute without asking if confidence >= 98%
