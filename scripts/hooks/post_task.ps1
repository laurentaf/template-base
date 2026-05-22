Write-Host "🪝 Post-Task Hook: Formatting & Linting..." -ForegroundColor Cyan
uv run ruff format .
uv run ruff check . --fix
Write-Host "✅ Code Quality Sync Complete." -ForegroundColor Green
