@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"

REM --- Python: prefer py launcher, then python on PATH (only needed to create .venv) ---
set "PYCMD="
where py >nul 2>&1 && set "PYCMD=py -3"
if not defined PYCMD where python >nul 2>&1 && set "PYCMD=python"
if not defined PYCMD (
  echo No Python found. Install Python 3.11+ or add it to PATH, then run this again.
  exit /b 1
)

if not exist "%ROOT%.venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PYCMD% -m venv "%ROOT%.venv"
  if errorlevel 1 exit /b 1
)

set "VPY=%ROOT%.venv\Scripts\python.exe"
set "VPIP=%ROOT%.venv\Scripts\pip.exe"

echo Installing dependencies...
"%VPY%" -m pip install -q --upgrade pip
"%VPIP%" install -q -e ".[dev]"
if errorlevel 1 exit /b 1

echo Applying migrations and seeding database...
"%VPY%" "%ROOT%scripts\seed.py"
if errorlevel 1 exit /b 1

set "PORT=8000"
set "URL=http://127.0.0.1:%PORT%/v1/puzzle"

echo Starting API on %URL% ...
REM /D sets the new window's working directory so `app` imports resolve.
start "Jointed API (uvicorn)" /D "%ROOT%" cmd /k "%VPY%" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%

echo Waiting for server to listen...
REM ping delay avoids "Input redirection" issues that `timeout` has in some shells
ping -n 4 127.0.0.1 >nul

start "" "%URL%"
echo Opened browser. API logs are in the other window. Close that window to stop the server.
endlocal
exit /b 0
