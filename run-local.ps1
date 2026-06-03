$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiDir   = Join-Path $repoRoot 'Tiki_Project\api'
$webDir   = Join-Path $repoRoot 'Tiki_Project\website'
$venvDir  = Join-Path $apiDir 'venv'

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Stop-PortProcesses {
    param([int[]]$Ports)
    foreach ($port in $Ports) {
        $portPattern = ":$port"
        $netstatLines = netstat -ano -p tcp | Select-String -Pattern $portPattern | Select-String -Pattern "LISTENING"
        $targets = @()
        foreach ($line in $netstatLines) {
            $parts = ($line.Line -split '\s+') | Where-Object { $_ -ne '' }
            if ($parts.Length -ge 5) { $targets += $parts[-1] }
        }
        $targets = $targets | Select-Object -Unique
        foreach ($target in $targets) {
            try {
                $proc = Get-Process -Id $target -ErrorAction Stop
                Stop-Process -Id $target -Force -ErrorAction Stop
                Write-Host "  Stopped PID $target ($($proc.ProcessName)) on port $port" -ForegroundColor Yellow
            } catch {
                # Process may have already exited
            }
        }
    }
}

function Write-Section {
    param([string]$Title)
    Write-Host ''
    Write-Host ('=' * 60) -ForegroundColor DarkCyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host ('=' * 60) -ForegroundColor DarkCyan
}

function Write-OK   { param([string]$Msg) Write-Host "  [OK]   $Msg" -ForegroundColor Green }
function Write-WARN { param([string]$Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
function Write-FAIL { param([string]$Msg) Write-Host "  [FAIL] $Msg" -ForegroundColor Red }
function Write-INFO { param([string]$Msg) Write-Host "  [INFO] $Msg" -ForegroundColor Gray }

# ============================================================
# PRE-FLIGHT CHECKS
# ============================================================

Write-Section "TIKI BUSINESS ASSISTANT - Local Launcher"

# Check folders exist
if (-not (Test-Path $apiDir)) { Write-Error "API folder not found: $apiDir" }
if (-not (Test-Path $webDir)) { Write-Error "Website folder not found: $webDir" }

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-OK "Python found: $pythonVersion"
} catch {
    Write-FAIL "Python is not installed or not in PATH. Please install Python 3.10+"
    exit 1
}

# ============================================================
# STEP 1: Clean old processes
# ============================================================

Write-Section "Step 1/6: Cleaning old processes"
Stop-PortProcesses -Ports @(8000, 5501)
Write-OK "Ports 8000 and 5501 cleared"

# ============================================================
# STEP 2: Virtual Environment
# ============================================================

Write-Section "Step 2/6: Virtual Environment"

$venvPython   = Join-Path $venvDir 'Scripts\python.exe'
$venvPip      = Join-Path $venvDir 'Scripts\pip.exe'
$venvActivate = Join-Path $venvDir 'Scripts\Activate.ps1'
$needsInstall = $false

if (-not (Test-Path $venvPython)) {
    Write-WARN "venv not found. Creating..."
    Start-Process python -ArgumentList "-m venv venv" -WorkingDirectory $apiDir -NoNewWindow -Wait
    if (-not (Test-Path $venvPython)) {
        Write-FAIL "Failed to create virtual environment"
        exit 1
    }
    $needsInstall = $true
    Write-OK "Virtual environment created"
} else {
    # Quick dependency check
    $testResult = Start-Process $venvPython -ArgumentList "-c `"import fastapi, pydantic, pandas, uvicorn, groq`"" -WorkingDirectory $apiDir -NoNewWindow -PassThru -Wait
    if ($testResult.ExitCode -ne 0) {
        Write-WARN "Some dependencies missing in venv"
        $needsInstall = $true
    } else {
        Write-OK "Virtual environment OK (all core packages present)"
    }
}

if ($needsInstall) {
    Write-INFO "Installing/updating dependencies..."
    Start-Process $venvPython -ArgumentList "-m pip install --upgrade pip --quiet" -WorkingDirectory $apiDir -NoNewWindow -Wait
    Start-Process $venvPip -ArgumentList "install -r requirements.txt --quiet" -WorkingDirectory $apiDir -NoNewWindow -Wait
    Write-OK "Dependencies installed"
}

# ============================================================
# STEP 3: Validate .env Configuration
# ============================================================

Write-Section "Step 3/6: Checking .env Configuration"

$envFile = Join-Path $apiDir '.env'
if (-not (Test-Path $envFile)) {
    Write-FAIL ".env file not found at $envFile"
    Write-INFO "Create it with at minimum:"
    Write-INFO "  GROQ_API_KEY=gsk_your_key_here"
    Write-INFO "  GEMINI_API_KEY=your_gemini_key (optional)"
    Write-INFO "  DATA_PATH=../data"
    Write-INFO "  MODELS_PATH=../module"
    Write-INFO "  CHROMA_DB_PATH=../chroma_db"
    exit 1
}

$envContent = Get-Content $envFile -Raw

# Check GEMINI_API_KEY (PRIMARY - required for chat)
if ($envContent -match 'GEMINI_API_KEY=(.+)') {
    $geminiKeyPreview = $Matches[1].Trim().Substring(0, [Math]::Min(20, $Matches[1].Trim().Length)) + "..."
    Write-OK "GEMINI_API_KEY configured: $geminiKeyPreview - Primary chat provider"
} else {
    Write-FAIL "GEMINI_API_KEY not found in .env!"
    Write-INFO "Gemini is the PRIMARY chat provider."
    exit 1
}

# Check GROQ_API_KEY (optional fallback)
if ($envContent -match 'GROQ_API_KEY=(.+)') {
    $groqKeys = ($Matches[1].Trim() -split ',').Count
    Write-OK "GROQ_API_KEY configured ($groqKeys key(s)) (optional fallback)"
} else {
    Write-WARN "GROQ_API_KEY not set (optional - Gemini will handle all chat requests)"
}

# Check data paths
foreach ($varName in @('DATA_PATH', 'MODELS_PATH', 'CHROMA_DB_PATH')) {
    if ($envContent -match "$varName=(.+)") {
        Write-OK "$varName = $($Matches[1].Trim())"
    } else {
        Write-WARN "$varName not set in .env"
    }
}

# ============================================================
# STEP 4: Verify Data & Models
# ============================================================

Write-Section "Step 4/6: Verifying Data & Models"

$env:PYTHONIOENCODING = 'utf-8'
$verifyProcess = Start-Process $venvPython -ArgumentList "verify_setup.py" -WorkingDirectory $apiDir -NoNewWindow -PassThru -Wait
if ($verifyProcess.ExitCode -ne 0) {
    Write-WARN "Some verification warnings (server will still start)"
} else {
    Write-OK "All data and model checks passed"
}

# ============================================================
# STEP 5: Start Servers
# ============================================================

Write-Section "Step 5/6: Starting Servers"

# Backend (FastAPI + Uvicorn)
Write-INFO "Starting Backend API at http://localhost:8000 ..."
$backendCmd = @(
    "`$env:PYTHONIOENCODING = 'utf-8'",
    "& '$venvActivate'",
    "python main.py"
) -join '; '
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $backendCmd -WorkingDirectory $apiDir

# Wait for backend to be ready
Write-INFO "Waiting for backend to initialize..."
Start-Sleep -Seconds 4

# Frontend (Static HTTP Server)
Write-INFO "Starting Frontend at http://localhost:5501 ..."
$frontendCmd = @(
    "`$env:PYTHONIOENCODING = 'utf-8'",
    "python -m http.server 5501"
) -join '; '
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $frontendCmd -WorkingDirectory $webDir

# ============================================================
# STEP 6: Open Browser
# ============================================================

Write-Section "Step 6/6: Ready!"

Start-Sleep -Seconds 2
Start-Process 'http://localhost:5501'

Write-Host ''
Write-Host '  Architecture:' -ForegroundColor White
Write-Host '    Chat AI   : Gemini Flash (primary)' -ForegroundColor Green
Write-Host '    Backend   : http://localhost:8000' -ForegroundColor White
Write-Host '    Frontend  : http://localhost:5501' -ForegroundColor White
Write-Host '    API Docs  : http://localhost:8000/docs' -ForegroundColor White
Write-Host ''
Write-Host '  Troubleshooting:' -ForegroundColor Yellow
Write-Host '    1) Check Backend terminal for errors' -ForegroundColor Gray
Write-Host '    2) Verify GEMINI_API_KEY in Tiki_Project/api/.env' -ForegroundColor Gray
Write-Host ''
