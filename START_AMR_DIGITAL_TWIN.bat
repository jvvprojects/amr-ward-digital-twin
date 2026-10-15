@echo off
setlocal EnableExtensions
title AMR-Ward Digital Twin
rem ---------------------------------------------------------------------------
rem  One-click launcher. Works from any folder (uses the folder this file is in).
rem  First start: creates a private Python environment and installs components
rem  (needs internet once, a few minutes). Later starts: instant and work offline.
rem ---------------------------------------------------------------------------
cd /d "%~dp0"
set "APPDIR=%~dp0"
if not exist "%APPDIR%logs" mkdir "%APPDIR%logs"
set "LOG=%APPDIR%logs\startup_log.txt"
echo AMR-Ward Digital Twin launcher - %date% %time% > "%LOG%"
echo.
echo  AMR-Ward Digital Twin  -  simulated data, educational use only
echo  --------------------------------------------------------------

rem ---- 1. already set up? ----------------------------------------------------
if exist "%APPDIR%.venv\Scripts\python.exe" goto :check_deps

rem ---- 2. find a base Python (3.9 or newer) ----------------------------------
set "BASEPY="
py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
if not errorlevel 1 set "BASEPY=py -3"
if not defined BASEPY (
  python -c "import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
  if not errorlevel 1 set "BASEPY=python"
)
if defined BASEPY goto :make_venv

echo  Python 3.9 or newer was not found on this computer.
where winget >nul 2>&1
if errorlevel 1 goto :no_python
echo.
choice /C YN /M "  Install Python 3.12 automatically now (Windows Package Manager)"
if errorlevel 2 goto :no_python
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements >> "%LOG%" 2>&1
if errorlevel 1 goto :no_python
echo.
echo  Python was installed. Please CLOSE this window and double-click
echo  START_AMR_DIGITAL_TWIN.bat once more.
pause
exit /b 0

:no_python
echo.
echo  What to do:
echo    1. Go to https://www.python.org/downloads/ and install Python 3.12.
echo    2. IMPORTANT: tick "Add python.exe to PATH" on the first installer screen.
echo    3. Double-click START_AMR_DIGITAL_TWIN.bat again.
echo  (Or ask for the packaged version that needs no Python.)
echo  Details were saved to: %LOG%
pause
exit /b 1

:make_venv
echo  First start: preparing a private environment (one time only) ...
%BASEPY% -m venv "%APPDIR%.venv" >> "%LOG%" 2>&1
if errorlevel 1 goto :setup_failed

:check_deps
"%APPDIR%.venv\Scripts\python.exe" -c "import streamlit, plotly, pandas, numpy" >nul 2>&1
if not errorlevel 1 goto :run
echo  Installing components - needs internet, about 2 to 5 minutes. Please wait ...
"%APPDIR%.venv\Scripts\python.exe" -m pip install --upgrade pip >> "%LOG%" 2>&1
"%APPDIR%.venv\Scripts\python.exe" -m pip install -r "%APPDIR%requirements.txt" >> "%LOG%" 2>&1
if errorlevel 1 goto :setup_failed
echo  Components installed.

:run
echo  Starting the app - your browser will open automatically ...
"%APPDIR%.venv\Scripts\python.exe" "%APPDIR%run_app.py" 2> "%APPDIR%logs\app_log.txt"
if errorlevel 1 goto :app_failed
exit /b 0

:setup_failed
echo.
echo  Setup did not finish. Common causes: no internet connection on the first start,
echo  or a firewall / antivirus blocking pip. Connect to the internet and try again.
echo  Technical details were saved to:
echo     %LOG%
pause
exit /b 1

:app_failed
echo.
echo  The app stopped unexpectedly. The last messages were:
echo  ---------------------------------------------------
powershell -NoProfile -Command "Get-Content -Tail 15 -Path '%APPDIR%logs\app_log.txt'" 2>nul
echo  ---------------------------------------------------
echo  Full details: %APPDIR%logs\app_log.txt
pause
exit /b 1
