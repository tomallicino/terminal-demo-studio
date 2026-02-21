<#
.SYNOPSIS
    Run a terminal-demo-studio screenplay on Windows.

.DESCRIPTION
    PowerShell wrapper equivalent to run.sh for Windows users.
    Runs a screenplay through tds in auto mode.

.EXAMPLE
    .\run.ps1
    .\run.ps1 screenplays\my_demo.yaml
    .\run.ps1 screenplays\my_demo.yaml --output gif --output-dir outputs
#>

param(
    [Parameter(Position = 0)]
    [string]$Screenplay,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $Screenplay) {
    $Screenplay = Join-Path $ScriptDir "screenplays\dev_bugfix_workflow.yaml"
}

$env:PYTHONPATH = "$ScriptDir;$env:PYTHONPATH"

$allArgs = @("-m", "terminal_demo_studio.cli", "run", $Screenplay, "--mode", "auto")
if ($ExtraArgs) {
    $allArgs += $ExtraArgs
}

python @allArgs
