# Grounding Protocol — Mandatory Context

This document defines the mandatory context that ALL agents must load before
taking any action. Every agent response must be grounded in this context.

## 1. Project Identity
- **Name:** {{PROJECT_NAME}}
- **Template:** LTADE template-base v0.1
- **Stack:** Python 3.11, uv, DuckDB, Postgres/pgvector, Qdrant, Redis
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
- **Current tier:** {{EXECUTION_TIER}} (development / staging / production)
- **Tier rules:**
  - Development: Full access, test data only
  - Staging: Read-only prod-like data, no destructive operations
  - Production: Read-only queries, no DDL, no DML without explicit approval
