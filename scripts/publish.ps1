# Publish a new release: bump version, update version.json, tag, and let
# GitHub Actions build the Windows exe + Android APK and upload them.
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts/publish.ps1 -Version 1.0.1 -Notes "Bug fixes"
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$Notes = ""
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

# 1. Bump the version in app_info.py
$appInfo = "app_info.py"
$content = Get-Content $appInfo -Raw
$content = $content -replace 'APP_VERSION = "[\d.]+"', "APP_VERSION = `"$Version`""
Set-Content -Path $appInfo -Value $content -NoNewline

# 2. Resolve the GitHub repo (owner/name) so download URLs are correct
$repo = gh repo view --json nameWithOwner --jq .nameWithOwner
if (-not $repo) { Write-Error "gh not authenticated. Run: gh auth login"; exit 1 }

# 3. Write version.json (drives the in-app updater)
$tag = "v$Version"
$json = @{
    version     = $Version
    notes       = $Notes
    windows_url = "https://github.com/$repo/releases/download/$tag/SalesManagement.exe"
    android_url = "https://github.com/$repo/releases/download/$tag/SalesManagement.apk"
} | ConvertTo-Json
Set-Content -Path "version.json" -Value $json -Encoding UTF8

# 4. Commit and push
git add app_info.py version.json
git commit -m "Release $Version"
git push origin HEAD

# 5. Tag and push (triggers the build-release workflow)
git tag $tag
git push origin $tag

Write-Output "Pushed $tag. GitHub Actions is building the Windows exe and Android APK."
Write-Output "Download page: https://github.com/$repo/releases/latest"
