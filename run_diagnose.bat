@echo off
echo [DIAGNOSE] Running python diagnosis...
if not exist "venv\Scripts\python.exe" (
    echo VENV Python not found!
    exit /b 1
)
venv\Scripts\python.exe diagnose.py
pause
