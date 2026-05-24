# Prefect Knowledge Base

> **Purpose**: DAG orchestration, flows, tasks
> **MCP Validated**: 2026-05-24

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/flows-tasks.md](concepts/flows-tasks.md) | Flow and task decorators, dependencies |
| [concepts/scheduling.md](concepts/scheduling.md) | Cron, interval, and RRule schedules |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/dag-patterns.md](patterns/dag-patterns.md) | DAG construction with task dependencies |
| [patterns/retry-fallback.md](patterns/retry-fallback.md) | Retry policies, caching, and fallback strategies |

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Flows** | Container for orchestrated task execution |
| **Tasks** | Discrete units of work with retry and caching |
| **Scheduling** | Time-based and event-driven flow triggers |
| **DAG Orchestration** | Directed acyclic graph execution with dependencies |

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| data-engineer | index.md | Navigation and discovery |
