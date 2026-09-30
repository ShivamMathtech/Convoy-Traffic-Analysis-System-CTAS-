@echo off
REM CTAS one-command launcher for Windows.
title CTAS Launcher

set ROOT=%~dp0

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10+ not found. Install from https://www.python.org/downloads/
    pause & exit /b 1
)

echo Checking Node...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 18+ not found. Install from https://nodejs.org/
    pause & exit /b 1
)

cd /d %ROOT%backend
if not exist .venv (
    echo Creating Python venv...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

echo Starting backend on :8000 ...
start "CTAS Backend" cmd /k "cd /d %ROOT%backend && .venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"

cd /d %ROOT%frontend
if not exist node_modules (
    echo Installing frontend deps (first run, may take a few minutes)...
    call npm install
)

echo Starting frontend on :5173 ...
start "CTAS Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo.
echo ============================================
echo  CTAS is starting...
echo  Frontend: http://localhost:5173
echo  Backend:  http://localhost:8000  (docs: /docs)
echo ============================================
pause
