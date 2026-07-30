@echo off
title AI Video & Voice Generator Launcher
echo ========================================
echo Starting AI Video & Voice Generator...
echo ========================================

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: Set Model Cache Directories to Local Workspace
set "HF_HOME=%BASE_DIR%backend\models"
set "TORCH_HOME=%BASE_DIR%backend\models"
set "TTS_HOME=%BASE_DIR%backend\models"

:: Check and Install Backend Dependencies
echo [1/2] Checking Backend Dependencies...
cd /d "%BASE_DIR%backend"
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing python dependencies...
"%BASE_DIR%backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
"%BASE_DIR%backend\.venv\Scripts\python.exe" -m pip install -r requirements.txt

:: Start Backend
start "Backend API" cmd /c "cd /d "%BASE_DIR%backend" && set HF_HOME=%BASE_DIR%backend\models && set TORCH_HOME=%BASE_DIR%backend\models && set TTS_HOME=%BASE_DIR%backend\models && "%BASE_DIR%backend\.venv\Scripts\python.exe" -m uvicorn main:app --reload --port 8000"

:: Check and Install Frontend Dependencies
echo [2/2] Checking Frontend Dependencies...
cd /d "%BASE_DIR%frontend"
if not exist "node_modules" (
    echo Installing node modules...
    call npm install
)

:: Start Frontend
start "Frontend UI" cmd /c "cd /d "%BASE_DIR%frontend" && npm run dev"

echo ========================================
echo All services updated & launched!
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:5173
echo ========================================
pause
