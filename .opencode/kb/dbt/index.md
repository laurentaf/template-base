# dbt Knowledge Base

> **Purpose**: Data transformation, models, tests, materializations
> **MCP Validated**: 2026-05-24

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/models.md](concepts/models.md) | Models, refs, sources, macros |
| [concepts/materializations.md](concepts/materializations.md) | Table, view, incremental, ephemeral |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/testing.md](patterns/testing.md) | Schema tests, data tests, custom tests |
| [patterns/incremental.md](patterns/incremental.md) | Incremental models with unique keys and partitions |

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Models** | SQL-based transformations with ref() and source() |
| **Materializations** | Table, view, incremental, ephemeral strategies |
| **Tests** | Schema and data tests for quality enforcement |
| **Incremental** | Processing only new/changed data for efficiency |

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| data-engineer | index.md | Navigation and discovery |
