param(
    [switch]$Full
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[qa] Creating virtual environment..."
    python -m venv .venv
}

Write-Host "[qa] Installing dependencies..."
& $venvPython -m pip install -r backend\requirements.txt | Out-Host

Write-Host "[qa] Running scenario fixtures..."
& $venvPython backend\scripts\run_scenario_fixture_checks.py

Write-Host "[qa] Running unit tests..."
& $venvPython -m unittest backend.tests.test_session_manager -v
& $venvPython -m unittest backend.tests.test_sessions_api -v
& $venvPython -m unittest backend.tests.test_legacy_api_session_sync -v

Write-Host "[qa] Running session/golden checks..."
& $venvPython backend\scripts\run_session_golden_check.py
& $venvPython backend\scripts\run_session_fixture_matrix_check.py
& $venvPython backend\scripts\run_golden_path_check.py

if ($Full) {
    Write-Host "[qa] Running RC stability check..."
    & $venvPython backend\scripts\run_rc_stability_check.py
}

Write-Host "[qa] Done."

