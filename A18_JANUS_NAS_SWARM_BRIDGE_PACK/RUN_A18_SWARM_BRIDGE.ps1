param(
  [switch]$Once = $true,
  [switch]$DryRun = $true,
  [string]$Config = ""
)

$ErrorActionPreference = "Stop"
$PackRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Config) {
  $Config = Join-Path $PackRoot "A18_SWARM_BRIDGE\a18_swarm_config.example.json"
}

$Script = Join-Path $PackRoot "A18_SWARM_BRIDGE\a18_swarm_bridge.py"
$Args = @("--config", $Config)
if ($Once) { $Args += "--once" }
if ($DryRun) { $Args += "--dry-run" }

python $Script @Args
