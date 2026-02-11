@echo off
echo [DEBUG] Step 1: Echo works.
pause
echo [DEBUG] Step 2: Checking python in PATH...
where python
echo Errorlevel: %errorlevel%
pause
echo [DEBUG] Step 3: Checking venv python...
if exist "venv\Scripts\python.exe" (
    echo FOUND venv python
) else (
    echo NOT FOUND venv python
)
pause
echo [DEBUG] Step 4: Trying to run launcher with venv python...
venv\Scripts\python.exe launcher.py
echo Errorlevel: %errorlevel%
pause
exit
