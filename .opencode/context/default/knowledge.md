# Project Knowledge Context

## Stack
- **Language:** Python 3.11
- **Package Manager:** uv
- **Orchestration:** Prefect, LangGraph
- **Databases:** PostgreSQL/pgvector (:5433), DuckDB (local), Qdrant (:6333)
- **Observability:** Arize Phoenix (:6006)
- **Cache:** Redis (:6379)
- **Object Storage:** MinIO (:9000)

## Entry Points
| Purpose | Command |
|---------|---------|
| Run project | `uv run python src/main.py` |
| Run tests | `uv run pytest tests/ -v` |
| Format code | `uv run ruff format .` |
| Lint | `uv run ruff check .` |
| Start infra | `docker compose -f E:/projects/infra/docker-compose.yml up -d` |
| SDD validation | `uv run python spec/quality_gates.py validate --feature <name>` |

## Architecture
- **Pattern:** SDD-Harness with Medallion layers (Bronze → Silver → Gold)
- **Agent workers:** 5 async agents communicating via Redis
- **Multi-agent mode:** `docker compose up` or `ltade-agents`

## Business Context
[Describe the business domain, entities, and goals here]

## Rules
- No hardcoded secrets — use OS env vars
- Pydantic for ALL data models
- Every public function needs a docstring
- Ruff format before every commit
- Update MEMORY.md after every task
