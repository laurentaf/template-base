# Medallion Knowledge Base

> **Purpose**: Bronze/Silver/Gold data architecture
> **MCP Validated**: 2026-05-24

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/bronze-layer.md](concepts/bronze-layer.md) | Raw ingestion, append-only, schema-on-read |
| [concepts/silver-layer.md](concepts/silver-layer.md) | Cleaned, deduplicated, conformed data |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/gold-layer.md](patterns/gold-layer.md) | Aggregated, business-ready aggregations |
| [patterns/layer-transitions.md](patterns/layer-transitions.md) | Promotion rules, quality gates, idempotency |

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Bronze** | Raw data layer: append-only, full history, schema-on-read |
| **Silver** | Cleaned layer: deduplicated, typed, conformed data |
| **Gold** | Business layer: aggregated, curated, presentation-ready |
| **Quality Gates** | Validation checks before layer promotion |

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| data-engineer | index.md | Navigation and discovery |
