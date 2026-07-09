[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Source,
    [string]$InstallDirectory = (Join-Path $env:ProgramFiles "RoXX"),
    [string]$ProbeUrl = "https://127.0.0.1:8000/readyz"
)

$ErrorActionPreference = "Stop"
$target = Join-Path $InstallDirectory "roxx.exe"
$rollbackDirectory = Join-Path $env:ProgramData "RoXX\rollback"
$backup = Join-Path $rollbackDirectory ("roxx-{0}.exe" -f (Get-Date -AsUTC -Format "yyyyMMddTHHmmssZ"))
if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "Upgrade source not found: $Source" }
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Installed RoXX not found: $target" }

New-Item -ItemType Directory -Force -Path $rollbackDirectory | Out-Null
Copy-Item -LiteralPath $target -Destination $backup -Force

try {
    & $target windows-service stop
    Copy-Item -LiteralPath $Source -Destination $target -Force
    & $target windows-service start
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -Uri $ProbeUrl -SkipCertificateCheck -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
    }
    if (-not $ready) { throw "RoXX readiness check failed after upgrade" }
    Write-Host "RoXX upgraded successfully. Rollback binary: $backup"
} catch {
    Write-Warning "Upgrade failed; restoring $backup"
    Stop-Service -Name RoXXWebServer -Force -ErrorAction SilentlyContinue
    Copy-Item -LiteralPath $backup -Destination $target -Force
    & $target windows-service start
    Get-WinEvent -FilterHashtable @{LogName="Application"; ProviderName="RoXXWebServer"} -MaxEvents 50 -ErrorAction SilentlyContinue
    throw
}
