param(
    [Parameter(Mandatory = $true)]
    [string]$ApiKey,
    [string]$ModelType = "qwen3.5-plus",
    [string]$BaseUrl = "https://coding.dashscope.aliyuncs.com/v1",
    [ValidateSet("api_key", "member_token")]
    [string]$AuthMode = "api_key"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$script = Join-Path $repoRoot "scripts\windows\start-client.ps1"

& $script `
  -ApiKey $ApiKey `
  -Provider "openai_compatible" `
  -ModelType $ModelType `
  -BaseUrl $BaseUrl `
  -AuthMode $AuthMode

