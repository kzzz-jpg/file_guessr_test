@echo off
echo [INFO] Starting File Guessr...

:: Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run fix_environment.bat first.
    pause
    exit /b 1
)

:: Run the launcher directly using venv python
:: This avoids issues with activate.bat or global python interference
"venv\Scripts\python.exe" launcher.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application crashed with code %errorlevel%
    pause
)
