@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo       File Guessr - Integrated Deployer
echo ==================================================

:: --- Part 0: Check for Administrator Privileges ---
echo.
echo [0/5] Checking for Administrator privileges...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator.
) else (
    echo [!] This script requires Administrator privileges to configure Windows Services.
    echo [!] Attempting to elevate...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Ensure we are in the script's directory (crucial after elevation which defaults to System32)
cd /d "%~dp0"

:: --- Part 1: Cleanup Running Processes ---
echo.
echo [1/5] Preparing environment (closing active instances)...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM pythonw.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: --- Part 2: Python Environment Setup ---
echo.
echo [2/5] Setting up Python environment...
if exist "venv" (
    echo Existing virtual environment found. Removing...
    :RETRY_RMDIR
    rmdir /s /q venv >nul 2>&1
    if exist "venv" (
        echo [!] Warning: Could not remove venv folder. File might be locked.
        echo Please ensure NO other Python scripts are running.
        pause
        goto :RETRY_RMDIR
    )
)
echo Creating new virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create venv. Check Python installation.
    pause
    exit /b 1
)
echo Activating environment and installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (echo [ERROR] Dependency installation failed! & pause & exit /b 1)

:: --- Part 3: Elasticsearch Detection ---
echo.
echo [3/5] Detecting Elasticsearch...
set "ES_PATH="
where /r c:\ elasticsearch.bat > temp_es_path.txt 2>nul
set /p FIRST_PATH=<temp_es_path.txt
del temp_es_path.txt
if defined FIRST_PATH (
    for %%i in ("%FIRST_PATH%") do set "ES_BIN_DIR=%%~dpi"
    set "ES_HOME=!ES_BIN_DIR!\.."
    echo Detected Elasticsearch at: !ES_HOME!
) else (
    echo [!] Could not automatically find Elasticsearch.
    set /p ES_HOME="Please enter the path to your Elasticsearch folder (e.g. C:\elasticsearch-8.x): "
)
if not exist "!ES_HOME!\bin\elasticsearch-service.bat" (echo [ERROR] Could not find elasticsearch-service.bat & pause & goto :FINISH)

:: --- Part 4: Configure and Install Service ---
echo.
echo [4/5] Configuring Elasticsearch Settings...
set "CONFIG_FILE=!ES_HOME!\config\elasticsearch.yml"
echo Applying security and networking fixes to !CONFIG_FILE!...
copy "!CONFIG_FILE!" "!CONFIG_FILE!.bak" >nul 2>&1
powershell -Command "$c = gc '!CONFIG_FILE!'; $c = $c -replace 'xpack.security.enabled:.*', 'xpack.security.enabled: false'; $c = $c -replace 'enabled: true', 'enabled: false'; $c | Out-File -Encoding UTF8 '!CONFIG_FILE!'"

if not exist "!ES_HOME!\config\jvm.options.d" mkdir "!ES_HOME!\config\jvm.options.d"
echo Setting JVM heap size to 2GB...
(
    echo -Xms2g
    echo -Xmx2g
) > "!ES_HOME!\config\jvm.options.d\heap.options"

sc query "elasticsearch-service-x64" >nul 2>&1
if %errorlevel% equ 0 (
    echo stopping existing service...
    sc stop "elasticsearch-service-x64" >nul 2>&1
) else (
    echo Installing Elasticsearch service...
    call "!ES_HOME!\bin\elasticsearch-service.bat" install
)
echo Configuring service for Automatic startup...
sc config "elasticsearch-service-x64" start= auto
echo Starting service...
sc start "elasticsearch-service-x64"

:: --- Part 5: Shortcut and Finalization ---
echo.
echo [5/5] Finalizing setup...
python setup_shortcut.py
echo.
echo Verifying Elasticsearch connection (this may take 15-30 seconds)...
set /a retry=0
:WAIT_ES
powershell -Command "try { $resp = Invoke-WebRequest -Uri 'http://localhost:9200' -UseBasicParsing -TimeoutSec 1; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Elasticsearch is UP and RUNNING.
) else (
    set /a retry+=1
    if !retry! lss 15 (
        <nul set /p=.
        timeout /t 2 /nobreak >nul
        goto :WAIT_ES
    )
    echo ⚠️ Elasticsearch is still starting in the background. It should be ready soon.
)

:FINISH
echo.
echo ==================================================
echo [SUCCESS] Deployment complete!
echo ==================================================
pause
