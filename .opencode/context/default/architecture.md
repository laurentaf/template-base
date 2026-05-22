# Architecture Context

## Component Map
[Describe the main components and their relationships]

## Stack Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Package manager | uv | 10-100x faster than pip |
| Orchestration | Prefect + LangGraph | Prefect for DAGs, LangGraph for agents |
| Relational DB | PostgreSQL + pgvector | ACID + vector search in one DB |
| Local analytics | DuckDB | Embedded OLAP, zero-config |
| Vector search | Qdrant | Purpose-built, high-performance |
| Observability | Arize Phoenix | LLM tracing + debugging |

## Forbidden Patterns
- No bare `except:` clauses
- No `print()` for logging (use `logging` or Phoenix)
- No sync DB calls in hot paths
- No mutable global state
