param(
    [Parameter(Mandatory = $true)]
    [string]$ApiKey,
    [string]$ModelType = "qwen3.5-plus",
    [switch]$RunRc
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

Write-Host "[bailian] 1/3 Start backend (Bailian)..."
$backendScript = Join-Path $repoRoot "scripts\windows\start-backend-bailian.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$backendScript`"", "-ApiKey", "`"$ApiKey`"", "-ModelType", "`"$ModelType`""

Write-Host "[bailian] waiting 5 seconds for backend..."
Start-Sleep -Seconds 5

Write-Host "[bailian] 2/3 Run backend QA..."
$qaScript = Join-Path $repoRoot "scripts\windows\run-backend-qa.ps1"
if ($RunRc) {
    & $qaScript -Full
}
else {
    & $qaScript
}

Write-Host "[bailian] 3/3 Start client (Bailian preset)..."
$clientScript = Join-Path $repoRoot "scripts\windows\start-client-bailian.ps1"
& $clientScript -ApiKey $ApiKey -ModelType $ModelType -AuthMode "api_key"

