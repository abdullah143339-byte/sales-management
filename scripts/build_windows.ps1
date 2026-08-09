# Build the Windows desktop app into a single .exe with PyInstaller.
# Run from the project root:  powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

python scripts/make_icon.py

pyinstaller --noconfirm --clean --onefile --windowed `
    --name "SalesManagement" `
    --icon "assets/icon.ico" `
    --add-data "assets/login_bg.mp4;assets" `
    --hidden-import "PySide6.QtMultimedia" `
    --hidden-import "PySide6.QtMultimediaWidgets" `
    --hidden-import "PySide6.QtPrintSupport" `
    main.py

if (-not $?) { exit 1 }

$exe = "dist/SalesManagement.exe"
if (-not (Test-Path $exe)) { Write-Error "Build failed: $exe missing"; exit 1 }

# Bundle into a portable zip too
$zip = "dist/SalesManagement-$($env:SALES_VERSION -or 'dev').zip"
$zip = "dist/SalesManagement-portable.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $exe -DestinationPath $zip
Write-Output "Built: $exe"
Write-Output "Zip:   $zip"
