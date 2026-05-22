param(
    [string]$RepoName,
    [string]$Description = "AI Data Engineering project",
    [switch]$Private,
    [string]$GitHubToken = $env:GITHUB_TOKEN
)

if (-not $RepoName) {
    $RepoName = Split-Path -Leaf (Get-Location)
}

if (-not $GitHubToken) {
    Write-Host "ERROR: GITHUB_TOKEN not set." -ForegroundColor Red
    Write-Host "Set it in your .env file or environment variables." -ForegroundColor Yellow
    exit 1
}

Write-Host "Creating GitHub repository '$RepoName'..." -ForegroundColor Cyan

$body = @{
    name        = $RepoName
    description = $Description
    private     = $Private.IsPresent
    auto_init   = $false
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" `
        -Method POST `
        -Headers @{
            Authorization = "Bearer $GitHubToken"
            "Content-Type" = "application/json"
        } `
        -Body $body

    $repoUrl = $response.clone_url
    Write-Host "Repository created: $repoUrl" -ForegroundColor Green

    # Add remote and push
    git remote add origin $repoUrl
    git branch -M main
    git push -u origin main

    Write-Host "Code pushed to GitHub successfully!" -ForegroundColor Green

    # Update harness state
    uv run python -c "
from src.core.harness import ProjectHarness
h = ProjectHarness('$RepoName')
h.set_github_repo('$repoUrl')
print('Harness updated with GitHub repo URL.')
"
}
catch {
    Write-Host "ERROR: Failed to create repository." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
