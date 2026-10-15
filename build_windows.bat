@echo off
setlocal EnableExtensions
title Build AMR-Ward Digital Twin (Windows)
rem ---------------------------------------------------------------------------
rem  OPTIONAL: builds a folder-based Windows app with PyInstaller so that users
rem  need no Python. Run this ON WINDOWS, with Python 3.9+ installed, on the
rem  developer machine only. Output: dist\AMR_Ward_Digital_Twin\AMR_Ward_Digital_Twin.exe
rem
rem  STATUS: this script was NOT executed or tested by the author of this project
rem  (it was written on Linux). Streamlit + PyInstaller packaging is sensitive to
rem  versions - read README.md section "Optional: standalone Windows app".
rem ---------------------------------------------------------------------------
cd /d "%~dp0"
if not exist ".venv-build\Scripts\python.exe" (
  py -3 -m venv .venv-build || (echo Could not create build environment & pause & exit /b 1)
)
set "PY=.venv-build\Scripts\python.exe"
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r requirements.txt pyinstaller pytest || (echo Install failed & pause & exit /b 1)

echo Running tests first ...
"%PY%" -m pytest -q || (echo Tests failed - build stopped & pause & exit /b 1)

"%PY%" -m PyInstaller --noconfirm --clean --onedir --name AMR_Ward_Digital_Twin ^
  --collect-all streamlit --collect-all plotly --copy-metadata streamlit ^
  --copy-metadata plotly --copy-metadata pandas --copy-metadata numpy ^
  --hidden-import simulation --hidden-import patients --hidden-import scenarios ^
  --hidden-import analytics --hidden-import visualizations --hidden-import education ^
  --hidden-import reporting --hidden-import about_text ^
  --add-data "app.py;." --add-data "simulation.py;." --add-data "patients.py;." ^
  --add-data "scenarios.py;." --add-data "analytics.py;." --add-data "visualizations.py;." ^
  --add-data "education.py;." --add-data "reporting.py;." --add-data "about_text.py;." ^
  --add-data "data;data" ^
  run_app.py
if errorlevel 1 (echo Build failed & pause & exit /b 1)

echo.
echo Build finished. Test it: dist\AMR_Ward_Digital_Twin\AMR_Ward_Digital_Twin.exe
echo Distribute the WHOLE dist\AMR_Ward_Digital_Twin folder (zip it).
echo Windows SmartScreen or antivirus may warn about an unsigned app.
pause
