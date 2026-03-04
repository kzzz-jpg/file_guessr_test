@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo       File Guessr - Integrated Deployer
echo ==================================================

:: --- Part 1: Python Environment Setup ---
echo.
echo [1/3] Setting up Python environment...

if exist "venv" (
    echo Existing virtual environment found. Removing...
    rmdir /s /q venv
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
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Dependency installation failed!
    pause
    exit /b 1
)

:: --- Part 2: Elasticsearch Detection ---
echo.
echo [2/3] Detecting Elasticsearch...

:: Try to detect ES path
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

if not exist "!ES_HOME!\bin\elasticsearch-service.bat" (
    echo [ERROR] Could not find elasticsearch-service.bat in !ES_HOME!\bin
    echo Please make sure the path is correct.
    pause
    goto :FINISH
)

:: --- Part 3: Configure and Install Service ---
echo.
echo [3/3] Configuring Elasticsearch Settings...

:: 1. Disable Security
set "CONFIG_FILE=!ES_HOME!\config\elasticsearch.yml"
echo Disabling X-Pack security in !CONFIG_FILE!...
:: Create a backup
copy "!CONFIG_FILE!" "!CONFIG_FILE!.bak" >nul
:: Use powershell to replace or add the security setting
powershell -Command "(gc '!CONFIG_FILE!') -replace 'xpack.security.enabled:.*', 'xpack.security.enabled: false' | Out-File -Encoding UTF8 '!CONFIG_FILE!'"
findstr /C:"xpack.security.enabled: false" "!CONFIG_FILE!" >nul
if %errorlevel% neq 0 (
    echo xpack.security.enabled: false >> "!CONFIG_FILE!"
)

:: 2. Set RAM (2GB)
if not exist "!ES_HOME!\config\jvm.options.d" mkdir "!ES_HOME!\config\jvm.options.d"
echo Setting JVM heap size to 2GB...
(
echo -Xms2g
echo -Xmx2g
) > "!ES_HOME!\config\jvm.options.d\heap.options"

:: 3. Manage Service
sc query "elasticsearch-service-x64" >nul 2>&1
if %errorlevel% equ 0 (
    echo Elasticsearch service already installed. Stopping to apply new settings if running...
    sc stop "elasticsearch-service-x64" >nul 2>&1
) else (
    echo Installing Elasticsearch as a Windows service...
    call "!ES_HOME!\bin\elasticsearch-service.bat" install
)

echo Setting service to automatic startup...
sc config "elasticsearch-service-x64" start= auto

echo Starting Elasticsearch service...
sc start "elasticsearch-service-x64"

:FINISH
echo.
echo ==================================================
echo [SUCCESS] Deployment complete!
echo ==================================================
echo.
echo Settings Applied:
echo  - RAM: 2GB (fixed)
echo  - Security: Disabled
echo  - Service: Auto-start
echo.
echo Now you can run File Guessr using run.bat
echo.
pause
