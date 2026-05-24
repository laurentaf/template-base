# DuckDB Knowledge Base

> **Purpose**: Embedded OLAP, VSS vector search, Medallion layers
> **MCP Validated**: 2026-05-24

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/olap-basics.md](concepts/olap-basics.md) | Columnar storage, analytical queries |
| [concepts/vss-vector-search.md](concepts/vss-vector-search.md) | VSS extension for vector similarity search |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/medallion-layers.md](patterns/medallion-layers.md) | Bronze/Silver/Gold layer management in DuckDB |
| [patterns/pivot-analytics.md](patterns/pivot-analytics.md) | Pivot, window functions, aggregations |

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Embedded OLAP** | In-process analytical database with columnar engine |
| **VSS Extension** | Vector similarity search using HNSW indexes |
| **Medallion Layers** | Bronze/Silver/Gold data architecture patterns |
| **Parquet I/O** | Native Parquet read/write for data lake integration |

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| data-engineer | index.md | Navigation and discovery |
