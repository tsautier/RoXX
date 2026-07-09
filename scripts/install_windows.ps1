[CmdletBinding()]
param(
    [string]$Source = (Join-Path $PSScriptRoot "roxx.exe"),
    [string]$InstallDirectory = (Join-Path $env:ProgramFiles "RoXX"),
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "RoXX installation requires an elevated PowerShell session."
}
if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
    throw "RoXX executable not found: $Source"
}

New-Item -ItemType Directory -Force -Path $InstallDirectory | Out-Null
$destination = Join-Path $InstallDirectory "roxx.exe"
Copy-Item -LiteralPath $Source -Destination $destination -Force
& $destination windows-service install
if (-not $NoStart) {
    & $destination windows-service start
}
Write-Host "RoXX installed at $destination"
