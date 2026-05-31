param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$srcPath = Join-Path $projectRoot "src"
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    throw "Python executable not found at $pythonPath. Create the virtual environment first."
}

$env:PYTHONPATH = $srcPath

$args = @(
    "-m",
    "uvicorn",
    "researchos.api.main:app",
    "--host",
    $HostName,
    "--port",
    $Port
)

if (-not $NoReload) {
    $args += "--reload"
}

Write-Host "Starting ResearchOS API at http://$HostName`:$Port" -ForegroundColor Cyan
& $pythonPath @args
