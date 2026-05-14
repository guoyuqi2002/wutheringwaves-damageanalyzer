param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"

if ([string]::IsNullOrWhiteSpace($Version)) {
    try {
        $Version = (git describe --tags --always --dirty).Trim()
    } catch {
        $Version = "dev-" + (Get-Date -Format "yyyyMMdd-HHmmss")
    }
}

$safeVersion = $Version -replace '[^A-Za-z0-9._-]', '-'
$appName = "DamageAnalyzer-$safeVersion"
$distPath = Join-Path $PSScriptRoot "dist"
$buildPath = Join-Path $PSScriptRoot "build"
$exePath = Join-Path $distPath "$appName.exe"

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name $appName `
    --distpath $distPath `
    --workpath $buildPath `
    --specpath $buildPath `
    main.py

if (-not (Test-Path $exePath)) {
    throw "Build failed: $exePath was not created."
}

if (Test-Path $buildPath) {
    Remove-Item -LiteralPath $buildPath -Recurse -Force
}

Write-Host ""
Write-Host "Build complete: $exePath"
