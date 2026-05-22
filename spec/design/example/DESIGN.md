# Design: [Feature Name]

## Architecture

### Data Flow
```mermaid
flowchart LR
    Source --> Process --> Sink
```

### File Manifest
| File | Purpose | Agent |
|------|---------|-------|
| `src/pipelines/example.py` | Pipeline logic | `data-pipeline` |
| `tests/test_example.py` | Tests | `reviewer` |

## Schema Design
[Entity definitions, columns, types, constraints]

## ADRs
### ADR-001: [Decision]
- **Context:** [Why this decision needed to be made]
- **Decision:** [What we decided]
- **Consequences:** [Trade-offs, impact]
