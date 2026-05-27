param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectName,
    [string]$TemplatePath = "",
    [string]$ProjectsRoot = ""
)

if (-not $TemplatePath) {
    $TemplatePath = Split-Path -Parent $PSScriptRoot
}
if (-not $ProjectsRoot) {
    $ProjectsRoot = Split-Path -Parent $TemplatePath
}

$Destination = Join-Path $ProjectsRoot $ProjectName

if (Test-Path $Destination) {
    Write-Host "ERROR: Destination '$Destination' already exists." -ForegroundColor Red
    exit 1
}

Write-Host "[1/5] Creating project from template..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
Get-ChildItem -Path $TemplatePath -Force | Copy-Item -Destination $Destination -Recurse -Force

Set-Location $Destination

Write-Host "[2/5] Initializing Python environment (uv)..." -ForegroundColor Cyan
uv venv
uv sync

Write-Host "[3/5] Initializing project harness..." -ForegroundColor Cyan
uv run python src/core/harness.py

Write-Host "[4/5] Initializing git repository..." -ForegroundColor Cyan
git init
git add .
git commit -m "Initial commit: scaffold from LTADE template"

Write-Host "[5/5] Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Location: $Destination" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. cd $Destination"
Write-Host "  2. .venv\Scripts\activate"
Write-Host "  3. opencode ."
Write-Host "  4. Update spec/design.md with your architecture plan"
Write-Host "  5. Edit .env with your API keys"
Write-Host ""
Write-Host "To deploy to GitHub:"
Write-Host "  powershell scripts\deploy_to_github.ps1"
