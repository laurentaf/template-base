# Agent Overrides

Any agent in this directory can be overridden locally without modifying the
template. Create a file in one of these locations:

| Scope | Location | Priority |
|-------|----------|----------|
| Project | `.opencode/agents/<name>.md` | Highest |
| Global | `~/.config/opencode/agents/<name>.md` | Medium |
| Template | `.opencode/agents/<name>.md` (this) | Lowest |

## How to Override

### Change an agent's prompt
Create `.opencode/agents/data-engineer.md` and it will take precedence
over the template version. Copy the frontmatter from the template agent
and modify the body.

### Disable an agent
In `opencode.json`:
```json
"agent": {
  "reviewer": { "disable": true }
}
```

### Add a new custom agent
Create `.opencode/agents/my-agent.md` and register it in `opencode.json`:
```json
"agent": {
  "my-agent": {
    "description": "Custom agent for specific tasks",
    "mode": "subagent"
  }
}
```

### Override via Environment
Set `OPENCODE_DISABLE_PROJECT_CONFIG=1` to skip all project-level config
and load from globals only. Useful for recovering from a broken override.
