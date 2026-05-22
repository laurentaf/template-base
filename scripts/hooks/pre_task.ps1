Write-Host "🪝 Pre-Task Hook: Checking Plan..." -ForegroundColor Cyan
if (!(Test-Path "spec/todo.md")) {
    Write-Host "❌ ERROR: No plan found in spec/todo.md!" -ForegroundColor Red
    Write-Host "Please create a design plan before writing code." -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Plan detected. Proceeding..." -ForegroundColor Green
