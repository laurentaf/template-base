# Contributing

## Development Setup

```powershell
uv venv
uv sync --dev
```

## Code Style

This project uses Ruff for formatting and linting:

```powershell
uv run ruff format .
uv run ruff check .
```

## Testing

```powershell
uv run pytest tests/ -v
```

## Pull Request Process

1. Update `spec/design.md` if changing architecture
2. Update `MEMORY.md` with changes made
3. Ensure all tests pass
4. Run Ruff formatting
5. Update `spec/lessons.md` if you learned something new

## Commit Messages

Follow conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
