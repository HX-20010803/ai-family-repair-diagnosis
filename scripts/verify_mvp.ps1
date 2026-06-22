param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [int]$Port = 8000,
    [string]$DatabaseUrl = "postgresql+psycopg://repair:repair@localhost:5432/repair_ai",
    [switch]$StartBackend,
    [switch]$SkipFrontend,
    [string]$PnpmPath = "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$BackendJob = $null

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Block
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Block
    Write-Host "OK: $Name" -ForegroundColor Green
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$Retries = 60
    )

    for ($i = 0; $i -lt $Retries; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "Service did not become ready: $Url"
}

try {
    Set-Location $RootDir

    Invoke-Step "Backend unit tests" {
        python -m unittest backend.tests.test_config backend.tests.test_knowledge_base backend.tests.test_core_services backend.tests.test_llm_adapter backend.tests.test_persistence_flow
    }

    Invoke-Step "Alembic migration" {
        Push-Location $BackendDir
        try {
            $env:DATABASE_URL = $DatabaseUrl
            python -m alembic upgrade head
        } finally {
            Pop-Location
        }
    }

    if ($StartBackend) {
        $BaseUrl = "http://127.0.0.1:$Port"
        Invoke-Step "Start temporary backend" {
            $occupied = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
            if ($occupied) {
                throw "Port $Port is already occupied. Stop the existing backend or pass a free -Port value."
            }
            $BackendJob = Start-Job -ScriptBlock {
                param($WorkDir, $DbUrl, $ListenPort)
                Set-Location $WorkDir
                $env:DATABASE_URL = $DbUrl
                python -m uvicorn app.main:app --host 127.0.0.1 --port $ListenPort
            } -ArgumentList $BackendDir, $DatabaseUrl, $Port
            Wait-HttpReady "$BaseUrl/api/v1/health"
        }
    } else {
        Invoke-Step "Check running backend" {
            Wait-HttpReady "$BaseUrl/api/v1/health" 10
        }
    }

    Invoke-Step "Deploy smoke" {
        python backend\scripts\deploy_smoke.py $BaseUrl
    }

    Invoke-Step "LLM smoke" {
        python backend\scripts\llm_smoke.py $BaseUrl
    }

    if (-not $SkipFrontend) {
        if (-not (Test-Path $PnpmPath)) {
            throw "pnpm executable not found: $PnpmPath"
        }

        Invoke-Step "Frontend typecheck" {
            Push-Location $FrontendDir
            try {
                & $PnpmPath run typecheck
            } finally {
                Pop-Location
            }
        }

        Invoke-Step "Frontend H5 build" {
            Push-Location $FrontendDir
            try {
                & $PnpmPath run build:h5
            } finally {
                Pop-Location
            }
        }
    }

    Write-Host ""
    Write-Host "MVP verification passed." -ForegroundColor Green
} finally {
    if ($BackendJob -ne $null) {
        Stop-Job $BackendJob -ErrorAction SilentlyContinue
        Receive-Job $BackendJob -ErrorAction SilentlyContinue | Select-Object -Last 40
        Remove-Job $BackendJob -Force -ErrorAction SilentlyContinue
    }
}
