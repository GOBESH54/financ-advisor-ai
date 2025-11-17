@echo off
cls
echo ========================================
echo Personal Finance Advisor - Core Launch
echo ========================================

REM Check if database exists
if not exist "backend\finance_advisor.db" (
    echo Initializing database...
    python init_db.py
)

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ❌ Virtual environment not found!
    echo Please run setup_minimal.bat first.
    pause
    exit /b 1
)

echo ✅ Starting backend server...
cd backend
start "Finance Advisor Backend" cmd /k "..\.venv\Scripts\python.exe app.py"
cd ..

timeout /t 3 /nobreak >nul

echo ✅ Backend started at http://localhost:5000

REM Check if Node.js is available for frontend
where npm >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================
    echo 🎉 Backend Started Successfully!
    echo ========================================
    echo 📊 API Server: http://localhost:5000
    echo 📖 Features Available:
    echo    • Bank statement upload & parsing
    echo    • Transaction categorization
    echo    • Basic budgeting & reporting  
    echo    • Data visualization
    echo    • Secure local processing
    echo.
    echo To add frontend:
    echo 1. Install Node.js from https://nodejs.org
    echo 2. Run: cd frontend && npm install && npm start
    echo.
    echo Press Ctrl+C to stop the backend server.
    pause
    goto :end
)

echo ✅ Starting frontend server...
cd frontend

if not exist "node_modules" (
    echo 📦 Installing frontend dependencies...
    npm install --silent
)

start "Finance Advisor Frontend" cmd /k "npm start"
cd ..

echo.
echo ========================================
echo 🎉 Personal Finance Advisor Started!
echo ========================================
echo 📊 Backend:  http://localhost:5000
echo 🌐 Frontend: http://localhost:3000 (starting...)
echo ========================================
echo.
echo Core Features Available:
echo ✅ Flask web application
echo ✅ Bank statement upload (PDF, CSV, Excel)
echo ✅ Transaction parsing & categorization
echo ✅ Indian banking support (HDFC, ICICI, SBI, etc.)
echo ✅ Basic budgeting & expense tracking
echo ✅ Interactive charts & reports
echo ✅ Secure local data processing
echo.
echo Advanced AI Features (install separately):
echo ⏸️ LSTM expense forecasting
echo ⏸️ Advanced anomaly detection  
echo ⏸️ Investment recommendations
echo.
timeout /t 10 /nobreak >nul
start http://localhost:3000

:end
echo.
echo Keep this window open. Press Ctrl+C to stop servers.
pause
