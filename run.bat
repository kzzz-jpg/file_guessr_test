@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo       File Guessr - Setup & Launch Script
echo ==================================================

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: 2. Check Ollama
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama not found!
    echo Please install Ollama from https://ollama.com/
    pause
    exit /b 1
)

:: 3. Setup Virtual Environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: 4. Activate Venv & Install Dependencies
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Installing/Updating dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: 5. Pull Ollama Model
echo [INFO] Checking Ollama model (gemma3:4b)...
ollama list | findstr "gemma3:4b" >nul
if %errorlevel% neq 0 (
    echo [INFO] Model not found. Pulling gemma3:4b...
    ollama pull gemma3:4b
) else (
    echo [INFO] Model gemma3:4b ready.
)

:: 6. Launch Application
echo [INFO] Starting File Guessr server...
echo.
echo ==================================================
echo   Server running at: http://127.0.0.1:8000
echo   Press Ctrl+C to stop the server
echo ==================================================
echo.

:: Open browser in background
start "" "http://127.0.0.1:8000"

python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

pause
