param(
    [string]$PythonExe = "python",
    [string]$OutputDir = "dist",
    [ValidateSet("wheel", "sdist", "all")]
    [string]$Artifact = "all"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
$ResolvedOutputDir = if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir
} else {
    Join-Path $ProjectRoot $OutputDir
}

New-Item -ItemType Directory -Force -Path $ResolvedOutputDir | Out-Null

# Use pip wheel instead of `python -m build`: the ignored top-level build/
# artifact directory can shadow PyPA's build module when running from repo root.
if ($Artifact -in @("wheel", "all")) {
    & $PythonExe -m pip wheel $ProjectRoot --no-deps --wheel-dir $ResolvedOutputDir
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    $Wheel = Get-ChildItem -LiteralPath $ResolvedOutputDir -Filter "b4user-*.whl" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -eq $Wheel) {
        Write-Error "No b4user wheel was created in $ResolvedOutputDir"
        exit 1
    }

    Write-Output "wheel=$($Wheel.FullName)"
}

if ($Artifact -in @("sdist", "all")) {
    $env:B4USER_PACKAGE_OUTPUT_DIR = $ResolvedOutputDir
    $SdistScript = @'
import os
from pathlib import Path
import setuptools.build_meta as build_meta

output_dir = Path(os.environ["B4USER_PACKAGE_OUTPUT_DIR"]).resolve()
output_dir.mkdir(parents=True, exist_ok=True)
artifact = build_meta.build_sdist(str(output_dir))
print(f"sdist={output_dir / artifact}")
'@
    $SdistScript | & $PythonExe -
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    $Sdist = Get-ChildItem -LiteralPath $ResolvedOutputDir -Filter "b4user-*.tar.gz" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -eq $Sdist) {
        Write-Error "No b4user sdist was created in $ResolvedOutputDir"
        exit 1
    }
}
