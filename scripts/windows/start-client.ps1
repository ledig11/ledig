param(
    [string]$ApiKey = "",
    [string]$Provider = "openai",
    [string]$ModelType = "gpt-4.1",
    [string]$BaseUrl = "https://api.openai.com/v1/responses",
    [ValidateSet("member_token", "api_key")]
    [string]$AuthMode = "api_key"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
    $env:OPENAI_API_KEY = $ApiKey
}

# These are read by StartupConfigWindow to prefill fields.
$env:WINDOWS_STEP_GUIDE_CLIENT_PROVIDER = $Provider
$env:WINDOWS_STEP_GUIDE_CLIENT_MODEL_TYPE = $ModelType
$env:WINDOWS_STEP_GUIDE_CLIENT_BASE_URL = $BaseUrl
$env:WINDOWS_STEP_GUIDE_CLIENT_AUTH_MODE = $AuthMode
if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
    $env:WINDOWS_STEP_GUIDE_CLIENT_API_KEY = $ApiKey
}

Write-Host "[client] Building windows client..."
dotnet build windows-client\WindowsStepGuide.Client.csproj -c Release

Write-Host "[client] Starting windows client..."
dotnet run --project windows-client\WindowsStepGuide.Client.csproj

