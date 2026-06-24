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
    "build_standalone_release.ps1",
    "extract_contract.py",
    "HUONG_DAN.md",
    "install_python_windows.ps1",
    "playwright_uploader.py",
    "README.md",
    "review_regex_samples.py",
    "requirements.txt",
    "run_ui.bat",
    "ui_runner.py",
    "uploader_selectors.py"
)

$directoriesToCopy = @(
    "ui",
    "ui_qt"
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
        if ($directoryName -eq "ui_qt") {
            continue
        }
        throw "Khong tim thay thu muc can phat hanh: $directoryName"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $releaseRoot $directoryName) -Recurse -Force
}

$regexReviewRoot = Join-Path $releaseRoot "regex_review_samples"
New-Item -ItemType Directory -Path (Join-Path $regexReviewRoot "input") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $regexReviewRoot "reports") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $toolRoot "regex_review_samples\.gitignore") -Destination (Join-Path $regexReviewRoot ".gitignore") -Force
Copy-Item -LiteralPath (Join-Path $toolRoot "regex_review_samples\README.md") -Destination (Join-Path $regexReviewRoot "README.md") -Force
New-Item -ItemType File -Path (Join-Path $regexReviewRoot "input\.gitkeep") -Force | Out-Null
New-Item -ItemType File -Path (Join-Path $regexReviewRoot "reports\.gitkeep") -Force | Out-Null

Write-Host "[OK] Da tao ban standalone tai: $releaseRoot"
