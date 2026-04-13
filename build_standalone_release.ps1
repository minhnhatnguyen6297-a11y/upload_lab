param(
    [string]$DestinationRoot = ""
)

$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $DestinationRoot) {
    $DestinationRoot = Join-Path $toolRoot "_release"
}
$releaseRoot = Join-Path $DestinationRoot "upload_lab"

$filesToCopy = @(
    ".env.example",
    "__init__.py",
    "batch_scan.py",
    "bootstrap_ui.py",
    "bootstrap_ui_pyqt6.py",
    "build_standalone_release.ps1",
    "extract_contract.py",
    "HUONG_DAN.md",
    "install_python_windows.ps1",
    "playwright_uploader.py",
    "README.md",
    "requirements.txt",
    "run_ui.bat",
    "run_ui_pyqt6.bat",
    "ui_app_pyqt6.py",
    "ui_runner.py",
    "uploader_selectors.py"
)

$directoriesToCopy = @(
    "ui"
)

if (Test-Path -LiteralPath $releaseRoot) {
    Remove-Item -LiteralPath $releaseRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

foreach ($fileName in $filesToCopy) {
    $source = Join-Path $toolRoot $fileName
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Khong tim thay file can phat hanh: $fileName"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $releaseRoot $fileName) -Force
}

foreach ($directoryName in $directoriesToCopy) {
    $source = Join-Path $toolRoot $directoryName
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Khong tim thay thu muc can phat hanh: $directoryName"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $releaseRoot $directoryName) -Recurse -Force
}

Write-Host "[OK] Da tao ban standalone tai: $releaseRoot"
