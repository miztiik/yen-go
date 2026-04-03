# Download KataGo and model for Windows (PowerShell)
# Run from the repository root: .\tools\download-katago.ps1

$ErrorActionPreference = "Stop"

$KATAGO_VERSION = "v1.15.3"
$MODEL_NAME = "kata1-b18c384nbt-s9131461376-d4087399203.bin.gz"
# Models are hosted on katagotraining.org, not GitHub releases
$MODEL_URL = "https://media.katagotraining.org/uploaded/networks/models/kata1/$MODEL_NAME"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$KataGoDir = Join-Path $ScriptDir "katago"

Write-Host "=== KataGo Setup for Yen-Go ===" -ForegroundColor Green
Write-Host "Directory: $KataGoDir"
Write-Host ""

# Create directories
New-Item -ItemType Directory -Force -Path $KataGoDir | Out-Null
New-Item -ItemType Directory -Force -Path "$KataGoDir\models" | Out-Null

# Download KataGo for Windows
$KataGoFile = "katago-$KATAGO_VERSION-eigen-windows-x64.zip"
$KataGoUrl = "https://github.com/lightvector/KataGo/releases/download/$KATAGO_VERSION/$KataGoFile"
$KataGoZip = Join-Path $KataGoDir $KataGoFile

if (-not (Test-Path "$KataGoDir\katago.exe")) {
    Write-Host "Downloading KataGo for Windows..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $KataGoUrl -OutFile $KataGoZip -UseBasicParsing
    
    Write-Host "Extracting..."
    Expand-Archive -Path $KataGoZip -DestinationPath $KataGoDir -Force
    Remove-Item $KataGoZip
    
    # Move files from subfolder if needed
    $SubFolder = Join-Path $KataGoDir "katago-$KATAGO_VERSION-eigen-windows-x64"
    if (Test-Path $SubFolder) {
        Get-ChildItem $SubFolder | Move-Item -Destination $KataGoDir -Force
        Remove-Item $SubFolder -Recurse
    }
    
    Write-Host "KataGo executable ready: $KataGoDir\katago.exe" -ForegroundColor Green
} else {
    Write-Host "KataGo already exists: $KataGoDir\katago.exe" -ForegroundColor Yellow
}

# Download model
$ModelPath = Join-Path "$KataGoDir\models" $MODEL_NAME

if (-not (Test-Path $ModelPath)) {
    Write-Host ""
    Write-Host "Downloading model: $MODEL_NAME..." -ForegroundColor Cyan
    Write-Host "(This may take a few minutes - ~500MB file)"
    Invoke-WebRequest -Uri $MODEL_URL -OutFile $ModelPath -UseBasicParsing
    Write-Host "Model downloaded to: $ModelPath" -ForegroundColor Green
} else {
    Write-Host "Model already exists: $ModelPath" -ForegroundColor Yellow
}

# Create analysis config
$ConfigContent = @"
# KataGo Analysis Config for Yen-Go Tsumego Validation
# Optimized for puzzle solving (not game playing)

# Number of search threads
numSearchThreads = 2

# Max visits per analysis (overridden by pipeline)
maxVisits = 200

# Analysis parameters
reportAnalysisWinratesAs = BLACK

# Neural net cache
nnCacheSizePowerOfTwo = 20
nnMutexPoolSizePowerOfTwo = 14

# For CPU backend (Eigen)
numNNServerThreadsPerModel = 1
"@

$ConfigContent | Out-File -FilePath "$KataGoDir\analysis.cfg" -Encoding UTF8

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "KataGo: $KataGoDir\katago.exe"
Write-Host "Model:  $ModelPath"
Write-Host "Config: $KataGoDir\analysis.cfg"
Write-Host ""
Write-Host "Test with:"
Write-Host "  cd $KataGoDir"
Write-Host "  .\katago.exe version"
