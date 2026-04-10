param(
    [string]$ApiKey = "",
    [string]$Provider = "openai",
    [string]$ModelType = "gpt-4.1",
    [string]$BaseUrl = "https://api.openai.com/v1/responses",
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[backend] Creating virtual environment..."
    python -m venv .venv
}

Write-Host "[backend] Installing dependencies..."
& $venvPython -m pip install -r backend\requirements.txt | Out-Host

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:OPENAI_API_KEY
}

$env:WINDOWS_STEP_GUIDE_MODEL_PROVIDER = $Provider
$env:WINDOWS_STEP_GUIDE_MODEL_TYPE = $ModelType
$env:WINDOWS_STEP_GUIDE_MODEL_BASE_URL = $BaseUrl
if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
    $env:OPENAI_API_KEY = $ApiKey
}

Write-Host "[backend] Starting FastAPI at http://$Host`:$Port ..."
& $venvPython -m uvicorn app.main:app --host $Host --port $Port --app-dir backend

