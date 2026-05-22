# AI Data Engineering Template

Template for **agentic data engineering projects** using the full AI-native stack: LangGraph, Prefect, DuckDB, PostgreSQL/pgvector, Qdrant, Arize Phoenix, and OpenCode.

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with WSL2 backend
- [OpenCode Desktop](https://opencode.ai)

### 1. Create a new project

```powershell
E:\projects\global-harness\setup_project.bat
```

Or manually:

```powershell
xcopy /E /I /H E:\projects\template-base E:\projects\my-new-project
cd E:\projects\my-new-project
uv venv
uv sync
```

### 2. Start infrastructure

```powershell
docker compose -f E:/projects/infra/docker-compose.yml up -d
E:/projects/global-harness/start_silver_infra.bat
```

### 3. Open in OpenCode

```powershell
opencode .
```

The `data-engineer` agent will load automatically with full MCP server access.

## Project Structure

```
.
├── opencode.json              # OpenCode configuration
├── .opencode/
│   ├── agents/
│   │   ├── data-engineer.md   # Primary AI Data Engineer agent
│   │   └── reviewer.md        # Code review subagent
│   └── skills/
│       └── data-engineering/  # Reusable data engineering skill
├── src/
│   ├── main.py                # Entry point
│   ├── core/
│   │   ├── config.py          # Pydantic settings (env-based)
│   │   ├── harness.py         # SDD-Harness state manager
│   │   ├── telemetry.py       # OpenTelemetry → Phoenix
│   │   ├── llm.py             # LLM client (NIM → OpenRouter)
│   │   └── decision_log.py    # Structured decision tracking
│   ├── agents/
│   │   └── base.py            # Base agent class (ABC)
│   ├── rag/
│   │   ├── ingest.py          # DuckDB VSS document ingestion
│   │   └── retrieve.py        # Semantic search retrieval
│   └── tools/
│       └── database.py        # DuckDB + Postgres connection helpers
├── spec/
│   ├── design.md              # Architecture spec (fill first)
│   ├── todo.md                # Active task plan
│   └── lessons.md             # Lessons learned
├── tests/
│   └── test_core.py           # pytest suite
├── scripts/
│   ├── hooks/                 # Pre/post task automation
│   ├── init_project.ps1       # PowerShell project init
│   └── deploy_to_github.ps1   # One-command GitHub deploy
├── docs/
│   └── knowledge_base.md      # AI-maintained project knowledge
├── .github/                   # CI/CD and issue templates
├── Dockerfile                 # Multi-stage production build
├── pyproject.toml              # Dependencies (uv)
├── MEMORY.md                   # Agent handoff state
└── .env                        # Local environment variables
```

## Tech Stack

| Component | Technology | Port |
|-----------|-----------|------|
| Orchestration | Prefect, LangGraph | 4200 |
| Relational DB | PostgreSQL 16 | 5433 |
| Vector Search | DuckDB VSS (local) | — |
| Object Storage | MinIO | 9000/9001 |
| Cache | Redis | 6379 |
| Observability | Arize Phoenix | 6006 |
| LLM Proxy | NVIDIA NIM Bridge | 8081 |

## MCP Servers

Configured in `opencode.json`:

| Server | Purpose |
|--------|---------|
| Filesystem | Project file read/write |
| GitHub | Repo management, PRs, issues |
| Postgres | Direct database queries |
| Docker | Container lifecycle |
| Sequential Thinking | Complex reasoning chains |
| Tavily | Web search for research |
| Exa | Semantic web search |
| Firecrawl | Web scraping |
| Context7 | Dependency analysis |

## Commands

```powershell
uv sync                   # Install dependencies
uv run pytest             # Run tests
uv run ruff format .      # Format code
uv run ruff check .       # Lint
uv run ltade              # CLI help (typer-based)
uv run ltade pipeline     # Run Medallion pipeline
uv run ltade decision add --title "..."   # Record a decision
uv run ltade rag ingest docs/ --db data/rag.duckdb  # Ingest docs for RAG
uv run ltade rag search "query"           # Semantic search
```

## Deployment to GitHub

```powershell
powershell scripts/deploy_to_github.ps1
```

Follow the prompts to create a new repo and push your project.
