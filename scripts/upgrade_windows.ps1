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
$backup = Join-Path $rollbackDirectory ("roxx-{0}-{1}.exe" -f (Get-Date -AsUTC -Format "yyyyMMddTHHmmssfffZ"), $PID)
if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "Upgrade source not found: $Source" }
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Installed RoXX not found: $target" }

function Wait-ExecutableUnlock {
    param([string]$Path)
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $stream = [System.IO.File]::Open($Path, 'Open', 'ReadWrite', 'None')
            $stream.Dispose()
            return
        } catch [System.IO.IOException] {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "RoXX executable remained locked after service stop: $Path"
}

New-Item -ItemType Directory -Force -Path $rollbackDirectory | Out-Null
Copy-Item -LiteralPath $target -Destination $backup -Force

try {
    & $target windows-service stop
    if ($LASTEXITCODE -ne 0) { throw "RoXX service stop failed with exit code $LASTEXITCODE" }
    (Get-Service -Name RoXXWebServer).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    Wait-ExecutableUnlock -Path $target
    Copy-Item -LiteralPath $Source -Destination $target -Force
    & $target windows-service start
    if ($LASTEXITCODE -ne 0) { throw "RoXX service start failed with exit code $LASTEXITCODE" }
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
    (Get-Service -Name RoXXWebServer).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    Wait-ExecutableUnlock -Path $target
    Copy-Item -LiteralPath $backup -Destination $target -Force
    & $target windows-service start
    if ($LASTEXITCODE -ne 0) { Write-Warning "Rollback service start failed with exit code $LASTEXITCODE" }
    Get-WinEvent -FilterHashtable @{LogName="Application"; ProviderName="RoXXWebServer"} -MaxEvents 50 -ErrorAction SilentlyContinue
    throw
}
