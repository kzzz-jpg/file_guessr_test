@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo       File Guessr - Launcher
echo ==================================================
echo.

:: --- Part 1: Ensure Elasticsearch is running ---
echo [INFO] Checking Elasticsearch service...
sc query "elasticsearch-service-x64" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Elasticsearch service not found. 
    echo Please run deploy.bat first to install the service.
    echo Searching will use SQLite fallback.
    goto :START_APP
)

:: Check if it's running
for /f "tokens=4" %%s in ('sc query "elasticsearch-service-x64" ^| findstr STATE') do set "ES_STATE=%%s"
if "!ES_STATE!" neq "RUNNING" (
    echo [INFO] Elasticsearch service is !ES_STATE!. Attempting to start...
    
    :: Try to start without elevation first (might work if permissions are set)
    sc start "elasticsearch-service-x64" >nul 2>&1
    
    :: Re-check
    timeout /t 2 /nobreak >nul
    for /f "tokens=4" %%s in ('sc query "elasticsearch-service-x64" ^| findstr STATE') do set "ES_STATE=%%s"
    if "!ES_STATE!" neq "RUNNING" (
        echo [!] Could not start service. Attempting to elevate...
        powershell -Command "Start-Process cmd -ArgumentList '/c sc start elasticsearch-service-x64' -Verb RunAs"
        
        echo [INFO] Waiting for service to initialize...
        timeout /t 5 /nobreak >nul
    )
)

:: Wait for ES to be responsive
echo [INFO] Waiting for Elasticsearch to be ready...
set /a retry_count=0
:WAIT_ES
powershell -Command "try { $resp = Invoke-WebRequest -Uri 'http://localhost:9200' -UseBasicParsing -TimeoutSec 1; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Elasticsearch is ready.
) else (
    set /a retry_count+=1
    if !retry_count! lss 10 (
        <nul set /p=.
        timeout /t 3 /nobreak >nul
        goto :WAIT_ES
    )
    echo.
    echo [WARNING] Elasticsearch timed out or connection refused.
    echo Searching might use SQLite fallback.
)

:START_APP
:: --- Part 2: Launch Application ---
:: Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run deploy.bat first.
    pause
    exit /b 1
)

echo.
echo [INFO] Starting File Guessr...
echo.

:: Run the launcher directly using venv python
"venv\Scripts\python.exe" launcher_bg.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application crashed with code %errorlevel%
)

pause
