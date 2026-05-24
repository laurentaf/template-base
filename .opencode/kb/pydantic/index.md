# Pydantic Knowledge Base

> **Purpose**: Data validation, structured outputs, settings
> **MCP Validated**: 2026-05-24

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/models.md](concepts/models.md) | BaseModel, validators, field constraints |
| [concepts/settings.md](concepts/settings.md) | BaseSettings, env vars, config management |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/structured-output.md](patterns/structured-output.md) | LLM structured output with Pydantic schemas |
| [patterns/validation-pipelines.md](patterns/validation-pipelines.md) | Chained validation and transformation |

## Key Concepts

| Concept | Description |
|---------|-------------|
| **BaseModel** | Declarative data models with automatic validation |
| **BaseSettings** | Environment-based configuration with type coercion |
| **Validators** | Custom field and model validators for business rules |
| **Structured Output** | Enforcing LLM responses into typed schemas |

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| data-engineer | index.md | Navigation and discovery |
