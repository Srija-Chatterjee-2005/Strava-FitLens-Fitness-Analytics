@echo off
setlocal
cd /d "%~dp0"
title FitLens - Fitness Analytics
if not exist "data\fitness.db" (
 echo Please extract the ENTIRE ZIP before running this file.
 pause
 exit /b 1
)
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if not errorlevel 1 (
 py -3 -m venv .venv
 goto checkenv
)
where python >nul 2>nul
if not errorlevel 1 (
 python -m venv .venv
 goto checkenv
)
echo Python was not found. Install Python 3.11 or 3.12, then run this file again.
pause
exit /b 1
:checkenv
if not exist ".venv\Scripts\python.exe" (
 echo Could not create the Python environment. Check your Python installation.
 pause
 exit /b 1
)
:install
echo Preparing FitLens. The first run needs internet to install packages.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
 echo Package setup failed. Check your internet connection and the message above.
 pause
 exit /b 1
)
echo Starting the dashboard. Keep this window open while using FitLens.
".venv\Scripts\python.exe" -m streamlit run app.py --theme.base light --theme.primaryColor "#e5484d" --theme.backgroundColor "#f6f7fb" --theme.secondaryBackgroundColor "#ffffff" --theme.textColor "#202536" --browser.gatherUsageStats false
pause
