param(
    [Parameter(Mandatory = $true)]
    [string]$Feature,
    [Parameter(Mandatory = $true)]
    [string]$Phase,  # brainstorm, define, design, build, ship
    [string]$SpecDir = "spec"
)

$PhaseOrder = @{
    "brainstorm" = 0
    "define"     = 1
    "design"     = 2
    "build"      = 3
    "ship"       = 4
}

$PhaseDirs = @{
    "brainstorm" = "brainstorm"
    "define"     = "define"
    "design"     = "design"
    "build"      = "build"
    "ship"       = "archive"
}

if (-not $PhaseOrder.ContainsKey($Phase)) {
    Write-Host "ERROR: Unknown phase '$Phase'. Use: brainstorm, define, design, build, ship" -ForegroundColor Red
    exit 1
}

$CurrentPhase = $PhaseOrder[$Phase]
$UpdatedDoc = Join-Path $SpecDir $PhaseDirs[$Phase] "$Feature\$($Phase.ToUpper()).md"

if (-not (Test-Path $UpdatedDoc)) {
    Write-Host "Updated document not found: $UpdatedDoc" -ForegroundColor Yellow
    Write-Host "Creating placeholder..."
    New-Item -ItemType File -Path $UpdatedDoc -Force | Out-Null
}

Write-Host "=== Cascade-Aware Iterate ===" -ForegroundColor Cyan
Write-Host "Feature: $Feature" -ForegroundColor Yellow
Write-Host "Updated phase: $Phase" -ForegroundColor Yellow
Write-Host ""

# Check downstream phases for staleness
Write-Host "Cascade check — downstream phases:" -ForegroundColor Cyan
$StaleFound = $false
foreach ($kv in $PhaseDirs.GetEnumerator()) {
    $PhaseName = $kv.Key
    $PhaseIdx = $PhaseOrder[$PhaseName]
    if ($PhaseIdx -gt $CurrentPhase) {
        $DocPath = Join-Path $SpecDir $kv.Value "$Feature\$($PhaseName.ToUpper()).md"
        if (Test-Path $DocPath) {
            Write-Host "  ⚠️  $PhaseName — EXISTS (may be stale after $Phase update)" -ForegroundColor Yellow
            $StaleFound = $true
        } else {
            Write-Host "  ✅ $PhaseName — not started yet, no cascade impact" -ForegroundColor Green
        }
    }
}

Write-Host ""
if ($StaleFound) {
    Write-Host "ACTION REQUIRED: Review downstream docs flagged above." -ForegroundColor Red
    Write-Host "Re-run their quality gates with:" -ForegroundColor Yellow
    Write-Host "  uv run python spec/quality_gates.py check --phase <phase> --feature $Feature"
} else {
    Write-Host "No cascade impact. All downstream phases are clean." -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Updated: $UpdatedDoc" -ForegroundColor Green
