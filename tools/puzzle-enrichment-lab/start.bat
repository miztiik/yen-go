@echo off
REM ═══════════════════════════════════════════════════════════
REM  Puzzle Enrichment Lab — Start Server (Windows)
REM ═══════════════════════════════════════════════════════════
REM
REM  Usage:
REM    start.bat              — Start on default port 8999
REM    start.bat 9000         — Start on custom port
REM
REM  KataGo is NOT required for the Browser (WebGPU) engine.
REM  Only install KataGo if you want to use the Local engine.
REM ═══════════════════════════════════════════════════════════

cd /d "%~dp0"

set PORT=%1
if "%PORT%"=="" set PORT=8999

echo.
echo   Puzzle Enrichment Lab
echo   Validate - Refute - Rate
echo   ========================
echo.

REM Kill any existing bridge process on this port
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":%PORT% " ^| findstr "LISTENING" 2^>nul') do (
    echo  Stopping existing process on port %PORT% (PID %%p)...
    taskkill /PID %%p /F >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM Auto-create config.json from template if missing
if not exist config.json (
    if exist config.example.json (
        copy config.example.json config.json >nul
        echo  [*] Created config.json from template.
    )
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

echo  Starting server on http://localhost:%PORT%
echo  Press Ctrl+C to stop.
echo.

set PORT=%PORT%
python bridge.py
