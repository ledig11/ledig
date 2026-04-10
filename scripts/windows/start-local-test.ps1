param(
    [string]$ApiKey = "",
    [switch]$RunRc
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

Write-Host "[local-test] 1/3 Start backend in new PowerShell window..."
$backendScript = Join-Path $repoRoot "scripts\windows\start-backend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$backendScript`"", "-ApiKey", "`"$ApiKey`""

Write-Host "[local-test] waiting 5 seconds for backend..."
Start-Sleep -Seconds 5

Write-Host "[local-test] 2/3 Run backend QA..."
$qaScript = Join-Path $repoRoot "scripts\windows\run-backend-qa.ps1"
if ($RunRc) {
    & $qaScript -Full
}
else {
    & $qaScript
}

Write-Host "[local-test] 3/3 Start client..."
$clientScript = Join-Path $repoRoot "scripts\windows\start-client.ps1"
& $clientScript -ApiKey $ApiKey

