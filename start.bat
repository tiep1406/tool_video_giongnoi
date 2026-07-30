@echo off
title AI Video and Voice Generator Launcher
echo ========================================
echo Starting AI Video and Voice Generator...
echo ========================================

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: Set Model Cache Directories to Local Workspace
set "HF_HOME=%BASE_DIR%backend\models"
set "TORCH_HOME=%BASE_DIR%backend\models"
set "TTS_HOME=%BASE_DIR%backend\models"

:: Check Backend Dependencies
echo [1/2] Checking Backend Dependencies...
cd /d "%BASE_DIR%backend"

if exist ".venv\Scripts\python.exe" goto CHECK_PIP

echo Creating virtual environment...
python -m venv .venv 2>nul
if exist ".venv\Scripts\python.exe" goto CHECK_PIP

py -m venv .venv 2>nul
if exist ".venv\Scripts\python.exe" goto CHECK_PIP

echo.
echo ========================================================
echo [LOI CRITICAL] Khong tim thay Python tren may tinh!
echo Vui long cai dat Python 3.10 tro len va TICH CHON "Add Python to PATH".
echo Link tai: https://www.python.org/downloads/
echo ========================================================
echo.
pause
exit /b 1

:CHECK_PIP
echo Installing python dependencies...
"%BASE_DIR%backend\.venv\Scripts\python.exe" -m ensurepip --default-pip >nul 2>nul
"%BASE_DIR%backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
"%BASE_DIR%backend\.venv\Scripts\python.exe" -m pip install -r requirements.txt

:: Check Frontend Dependencies
echo [2/2] Checking Frontend Dependencies...
cd /d "%BASE_DIR%frontend"

where npm >nul 2>nul
if %errorlevel% equ 0 goto CHECK_NODE_MODULES

echo.
echo ========================================================
echo [LOI CRITICAL] Khong tim thay Node.js / NPM tren may tinh!
echo Vui long cai dat Node.js LTS Version.
echo Link tai: https://nodejs.org/
echo ========================================================
echo.
pause
exit /b 1

:CHECK_NODE_MODULES
if exist "node_modules\" goto START_SERVICES
echo Installing node modules...
call npm install

:START_SERVICES
echo Starting Backend API...
start "Backend API" cmd /k "cd /d "%BASE_DIR%backend" && set HF_HOME=%BASE_DIR%backend\models && set TORCH_HOME=%BASE_DIR%backend\models && set TTS_HOME=%BASE_DIR%backend\models && "%BASE_DIR%backend\.venv\Scripts\python.exe" -m uvicorn main:app --reload --port 8000"

echo Starting Frontend UI...
start "Frontend UI" cmd /k "cd /d "%BASE_DIR%frontend" && npm run dev"

echo ========================================
echo All services launched successfully.
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:5173
echo ========================================
pause
