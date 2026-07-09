[CmdletBinding()]
param(
    [string]$InstallDirectory = (Join-Path $env:ProgramFiles "RoXX"),
    [switch]$KeepData
)

$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "RoXX removal requires an elevated PowerShell session."
}

$executable = Join-Path $InstallDirectory "roxx.exe"
if (Test-Path -LiteralPath $executable -PathType Leaf) {
    & $executable windows-service stop 2>$null
    & $executable windows-service remove
}
if (Test-Path -LiteralPath $InstallDirectory) {
    Remove-Item -LiteralPath $InstallDirectory -Recurse -Force
}
if (-not $KeepData) {
    $dataDirectory = Join-Path $env:ProgramData "RoXX"
    if (Test-Path -LiteralPath $dataDirectory) {
        Remove-Item -LiteralPath $dataDirectory -Recurse -Force
    }
}
Write-Host "RoXX removed."
