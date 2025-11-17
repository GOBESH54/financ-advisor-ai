@echo off
title Personal Finance Advisor - Launcher

:: Set colors for better visibility
color 0A
cls

echo ========================================
echo 🚀 Personal Finance Advisor - Auto Launcher
echo ========================================

:: Check Python installation
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.11 from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Set paths
set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%.venv"
set "BACKEND_DIR=%PROJECT_DIR%backend"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"

:: Create virtual environment if it doesn't exist
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Failed to create virtual environment
        echo Trying with administrator privileges...
        powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/c python -m venv "%VENV_DIR%"'"
        if %ERRORLEVEL% NEQ 0 (
            echo ❌ Still unable to create virtual environment
            echo Please try running as administrator
            pause
            exit /b 1
        )
    )
    echo ✅ Virtual environment created
    
    echo Installing Python dependencies...
    call "%VENV_DIR%\Scripts\activate.bat"
    pip install --upgrade pip
    pip install -r "%PROJECT_DIR%requirements.txt"
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Failed to install Python dependencies
        pause
        exit /b 1
    )
    echo ✅ Python dependencies installed
) else (
    call "%VENV_DIR%\Scripts\activate.bat"
)

:: Start backend
start "Finance Advisor Backend" cmd /k "cd /d "%BACKEND_DIR%" && "%VENV_DIR%\Scripts\python.exe" app.py"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Check if Node.js is installed
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo ⚠️  Node.js is not installed or not in PATH
    echo ========================================
    echo The backend is running at http://localhost:5000
    echo To enable the frontend:
    echo 1. Install Node.js from https://nodejs.org/
    echo 2. Run: cd frontend && npm install && npm start
    pause
    exit /b 0
)

:: Start frontend
cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install --silent
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Failed to install frontend dependencies
        pause
        exit /b 1
    )
)

start "Finance Advisor Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm start"

:: Show success message
echo.
echo ========================================
echo 🎉 Personal Finance Advisor Started!
echo ========================================
echo 📊 Backend:  http://localhost:5000
echo 🌐 Frontend: http://localhost:3000
echo.
echo Press any key to open in your browser...
pause >nul

start http://localhost:3000

exit /b 0
