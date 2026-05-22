param(
    [string]$ProjectName,
    [string]$Description = "AI Data Engineering project"
)

$ContextDir = ".opencode\context\$ProjectName"
$RegistryFile = ".opencode\context\registry.yaml"

if (-not (Test-Path $ContextDir)) {
    New-Item -ItemType Directory -Path $ContextDir -Force | Out-Null
}

# Copy default templates
Copy-Item ".opencode\context\default\*" $ContextDir -Force

# Update registry
if (Test-Path $RegistryFile) {
    $registry = Get-Content $RegistryFile -Raw
} else {
    $registry = "active_project: default`n`nprojects: {}"
}

# Simple YAML update (for production use a YAML library)
$entry = @"
  $ProjectName:
    path: $ContextDir
    description: $Description
    last_updated: $(Get-Date -Format "yyyy-MM-dd")
"@

Write-Host "Context created at $ContextDir" -ForegroundColor Green
Write-Host "To activate: edit .opencode/context/registry.yaml and set active_project: $ProjectName" -ForegroundColor Yellow
