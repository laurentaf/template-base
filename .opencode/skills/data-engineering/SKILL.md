---
name: data-engineering
description: Use when working on data pipelines, ETL/ELT, agentic data workflows, vector databases, or analytics with the LTADE stack (Prefect, LangGraph, DuckDB, Postgres, Qdrant, Phoenix).
---

# LTADE: Laurent Template AI Data Engineering

## Infrastructure (Run First)

```powershell
docker compose -f E:/projects/infra/docker-compose.yml up -d
E:/projects/global-harness/start_silver_infra.bat
```

## Essential MCP Servers

| Server | Purpose | Package |
|--------|---------|---------|
| Filesystem | Read/write project files | `@modelcontextprotocol/server-filesystem` |
| GitHub | Repo management, PRs, commits | `@modelcontextprotocol/server-github` |
| Postgres | SQL queries on project DB | `@anthropic/mcp-server-postgres` |
| Qdrant | Vector search operations | `@qbraid/qdrant-mcp-server` |
| Docker | Container lifecycle | `@anthropic/mcp-server-docker` |
| Sequential Thinking | Complex multi-step reasoning | `@anthropic/mcp-server-sequential-thinking` |

## Common Workflows

### Start a new project
```powershell
E:/projects/global-harness/setup_project.bat
```

### Run the stack
```powershell
uv sync
uv run python src/main.py
```

### Deploy to GitHub
```powershell
powershell scripts/deploy_to_github.ps1
```

## Telemetry & Debugging

- Traces: http://localhost:6006 (Phoenix)
- Vector search: http://localhost:6333/dashboard (Qdrant)
- MinIO console: http://localhost:9001
- Prefect UI: http://localhost:4200
