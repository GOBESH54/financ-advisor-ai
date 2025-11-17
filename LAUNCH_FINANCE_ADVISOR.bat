@echo off
title Personal Finance Advisor - Complete Setup & Launch
color 0A
cls

echo.
echo ██████╗ ███████╗██████╗ ███████╗ ██████╗ ███╗   ██╗ █████╗ ██╗     
echo ██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗████╗  ██║██╔══██╗██║     
echo ██████╔╝█████╗  ██████╔╝███████╗██║   ██║██╔██╗ ██║███████║██║     
echo ██╔═══╝ ██╔══╝  ██╔══██╗╚════██║██║   ██║██║╚██╗██║██╔══██║██║     
echo ██║     ███████╗██║  ██║███████║╚██████╔╝██║ ╚████║██║  ██║███████╗
echo ╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝
echo.
echo ███████╗██╗███╗   ██╗ █████╗ ███╗   ██╗ ██████╗███████╗
echo ██╔════╝██║████╗  ██║██╔══██╗████╗  ██║██╔════╝██╔════╝
echo █████╗  ██║██╔██╗ ██║███████║██╔██╗ ██║██║     █████╗  
echo ██╔══╝  ██║██║╚██╗██║██╔══██║██║╚██╗██║██║     ██╔══╝  
echo ██║     ██║██║ ╚████║██║  ██║██║ ╚████║╚██████╗███████╗
echo ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝
echo.
echo  █████╗ ██████╗ ██╗   ██╗██╗███████╗ ██████╗ ██████╗ 
echo ██╔══██╗██╔══██╗██║   ██║██║██╔════╝██╔═══██╗██╔══██╗
echo ███████║██║  ██║██║   ██║██║███████╗██║   ██║██████╔╝
echo ██╔══██║██║  ██║╚██╗ ██╔╝██║╚════██║██║   ██║██╔══██╗
echo ██║  ██║██████╔╝ ╚████╔╝ ██║███████║╚██████╔╝██║  ██║
echo ╚═╝  ╚═╝╚═════╝   ╚═══╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
echo.
echo ========================================================================
echo                     🚀 ADVANCED AI-POWERED FINANCE ADVISOR 🚀
echo ========================================================================
echo.
echo 🎯 Complete Feature Set:
echo    ✅ LSTM Deep Learning Forecasting (1-6 months ahead)
echo    ✅ AI Transaction Classification (20+ Indian categories)
echo    ✅ Anomaly Detection ^& Fraud Prevention
echo    ✅ Investment Recommendations (Random Forest ^& XGBoost)
echo    ✅ Indian Banking Support (HDFC, ICICI, SBI, AXIS, KOTAK, PNB, BOB)
echo    ✅ Multi-format Parsing (PDF, CSV, Excel, Images with OCR)
echo    ✅ UPI Integration (PhonePe, GPay, Paytm detection)
echo    ✅ Advanced Budgeting ^& Goal Tracking
echo    ✅ Business Intelligence ^& Analytics
echo    ✅ Security Features ^& Encryption
echo    ✅ Performance Optimization (8GB RAM optimized)
echo    ✅ Mobile-Responsive PWA Design
echo.
echo ========================================================================
echo.

REM Check system requirements
echo 🔍 Checking system requirements...

REM Check Python 3.11
python --version 2>nul | findstr "3.11" >nul
if errorlevel 1 (
    echo ❌ Python 3.11 is required but not found!
    echo Please install Python 3.11 from https://python.org
    echo.
    pause
    exit /b 1
)
echo ✅ Python 3.11 detected

REM Check Node.js (optional for frontend)
where npm >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Node.js not found - only backend will be available
    set FRONTEND_AVAILABLE=false
) else (
    echo ✅ Node.js detected
    set FRONTEND_AVAILABLE=true
)

echo.
echo 🛠️ Setup Options:
echo    [1] Complete Setup + Launch (Recommended)
echo    [2] Quick Launch (if already set up)
echo    [3] Clean Setup (remove old files + fresh install)
echo    [4] Backend Only
echo    [5] Exit
echo.
set /p choice="Select option (1-5): "

if "%choice%"=="1" goto complete_setup
if "%choice%"=="2" goto quick_launch
if "%choice%"=="3" goto clean_setup
if "%choice%"=="4" goto backend_only
if "%choice%"=="5" exit /b 0
goto invalid_choice

:complete_setup
echo.
echo 🚀 Starting Complete Setup...
echo ========================================================================

REM Run setup
call setup_env_python311.bat
if errorlevel 1 (
    echo ❌ Setup failed!
    pause
    exit /b 1
)

echo ✅ Setup completed successfully!
goto launch_app

:clean_setup
echo.
echo 🧹 Performing Clean Setup...
echo ========================================================================

REM Clean project
call cleanup_project.bat

REM Remove virtual environment
if exist ".venv" (
    echo Removing old virtual environment...
    rmdir /s /q .venv
)

REM Run fresh setup
call setup_env_python311.bat
if errorlevel 1 (
    echo ❌ Clean setup failed!
    pause
    exit /b 1
)

echo ✅ Clean setup completed successfully!
goto launch_app

:quick_launch
echo.
echo ⚡ Quick Launch...

REM Check if setup is complete
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found! Please run Complete Setup first.
    pause
    goto :eof
)

if not exist "backend\finance_advisor.db" (
    echo ❌ Database not found! Please run Complete Setup first.
    pause
    goto :eof
)

goto launch_app

:backend_only
echo.
echo 🔧 Starting Backend Only...
echo ========================================================================

if not exist ".venv\Scripts\activate.bat" (
    echo ❌ Please run setup first!
    pause
    goto :eof
)

call .venv\Scripts\activate.bat
cd backend
echo 🚀 Starting backend at http://localhost:5000
start "Finance Advisor Backend" cmd /k python app.py
cd ..

echo.
echo ✅ Backend started successfully!
echo 📊 API Available at: http://localhost:5000
echo 📖 Documentation: http://localhost:5000/api/docs
echo.
pause
goto :eof

:launch_app
echo.
echo 🚀 Launching Personal Finance Advisor...
echo ========================================================================

call .venv\Scripts\activate.bat

REM Start backend
echo 📊 Starting backend server...
cd backend
start "Finance Advisor Backend" cmd /k python app.py
cd ..

timeout /t 3 /nobreak >nul

if "%FRONTEND_AVAILABLE%"=="true" (
    REM Start frontend
    echo 🌐 Starting frontend server...
    cd frontend
    
    REM Install dependencies if needed
    if not exist "node_modules" (
        echo 📦 Installing frontend dependencies...
        npm install
    )
    
    start "Finance Advisor Frontend" cmd /k npm start
    cd ..
    
    echo.
    echo ✅ Application launched successfully!
    echo ========================================================================
    echo 📊 Backend API:    http://localhost:5000
    echo 🌐 Web Interface:  http://localhost:3000 (opening in 10 seconds...)
    echo ========================================================================
    
    timeout /t 10 /nobreak >nul
    start http://localhost:3000
) else (
    echo.
    echo ✅ Backend launched successfully!
    echo ========================================================================
    echo 📊 Backend API:    http://localhost:5000
    echo 📖 API Documentation: http://localhost:5000/api/docs
    echo ========================================================================
    echo.
    echo To use the web interface:
    echo 1. Install Node.js from https://nodejs.org
    echo 2. Restart this launcher
    echo.
)

echo.
echo 🎉 Personal Finance Advisor is now running!
echo.
echo 💡 Key Features Available:
echo    • Upload bank statements (PDF/CSV/Excel)
echo    • AI-powered transaction categorization
echo    • LSTM expense forecasting
echo    • Investment recommendations
echo    • Anomaly detection
echo    • Advanced budgeting
echo    • Business intelligence
echo    • Security dashboard
echo.
echo Press any key to close this launcher (app will continue running)...
pause >nul
goto :eof

:invalid_choice
echo ❌ Invalid choice. Please select 1-5.
pause
goto :eof
