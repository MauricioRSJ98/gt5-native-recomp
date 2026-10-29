param([Parameter(ValueFromRemainingArguments=$true)][string[]]$ReaArguments)
$ErrorActionPreference='Stop'
$projectPath=Split-Path $PSScriptRoot -Parent
if (-not $env:GHIDRA_INSTALL_DIR) { $env:GHIDRA_INSTALL_DIR=Join-Path $projectPath 'tools\ghidra_12.2_PUBLIC' }
if (-not $env:JAVA_HOME) { throw 'Set JAVA_HOME to your local JDK first.' }
$reaRoot=if($env:GT5_REA_ROOT){$env:GT5_REA_ROOT}else{Join-Path $projectPath 'tools\rea-runtime'}
$reaEntry=Join-Path $reaRoot 'node_modules\rea-agents\scripts\rea.mjs'
if(-not(Test-Path -LiteralPath $reaEntry)){throw 'Install REA locally or set GT5_REA_ROOT. See docs/CREDITS.md for integration limitations.'}
$env:TEMP=Join-Path $projectPath 'tools\rea-temp'
$env:TMP=$env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
& node $reaEntry @ReaArguments
exit $LASTEXITCODE
