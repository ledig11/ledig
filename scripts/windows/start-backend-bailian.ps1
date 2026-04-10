param(
    [Parameter(Mandatory = $true)]
    [string]$ApiKey,
    [string]$ModelType = "qwen3.5-plus",
    [string]$BaseUrl = "https://coding.dashscope.aliyuncs.com/v1",
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$script = Join-Path $repoRoot "scripts\windows\start-backend.ps1"

& $script `
  -ApiKey $ApiKey `
  -Provider "openai_compatible" `
  -ModelType $ModelType `
  -BaseUrl $BaseUrl `
  -Host $Host `
  -Port $Port

