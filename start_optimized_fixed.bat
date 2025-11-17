@echo off
cls
echo ========================================
echo Personal Finance Advisor - Optimized Launch
echo Python 3.11 Compatible Version
echo ========================================

REM Set optimized environment variables
set FLASK_APP=backend\app.py
set FLASK_ENV=development
set PYTHONPATH=%cd%\backend;%PYTHONPATH%

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found!
    echo Please run setup_env_python311.bat first.
    pause
    exit /b 1
)

echo ✅ Activating virtual environment...
call .venv\Scripts\activate.bat

REM Test if core dependencies are available
echo 🔍 Testing core dependencies...
python -c "import flask, pandas, numpy, matplotlib; print('✅ Core dependencies OK')" 2>nul
if errorlevel 1 (
    echo ❌ Core dependencies missing! Running setup...
    call setup_env_python311.bat
    if errorlevel 1 (
        echo ❌ Setup failed! Please check Python 3.11 installation.
        pause
        exit /b 1
    )
)

REM Create directories
if not exist "backend\uploads" mkdir backend\uploads
if not exist "backend\reports" mkdir backend\reports
if not exist "uploads" mkdir uploads
if not exist "reports" mkdir reports

REM Initialize database if needed
if not exist "backend\finance_advisor.db" (
    echo 🔧 Initializing database...
    cd backend
    python -c "
from flask import Flask
from models import db
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_advisor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()
    print('✅ Database initialized')
" 2>nul
    cd ..
)

echo ✅ Starting backend server...
cd backend
start "Finance Advisor Backend" cmd /k "python app.py"
cd ..

REM Wait for backend to start
timeout /t 5 /nobreak >nul

REM Test if backend is running
python -c "
import requests
try:
    r = requests.get('http://localhost:5000', timeout=5)
    print('✅ Backend is running')
except:
    print('⚠️ Backend may take a moment to start')
" 2>nul

REM Check if Node.js is available
where npm >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Node.js not found - backend only mode
    echo 📊 Backend running at: http://localhost:5000
    echo 📖 To use frontend: Install Node.js and run 'cd frontend && npm start'
    goto :end
)

REM Start frontend if Node.js is available
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
echo Features Available:
echo ✅ Core Flask application
echo ✅ Bank statement upload & parsing
echo ✅ Transaction categorization
echo ✅ Basic budgeting & reporting
echo ✅ Indian banking support
echo ✅ Secure local processing
echo.
echo AI/ML Features (depends on dependencies):
echo 📊 LSTM forecasting (if TensorFlow available)
echo 🤖 Advanced AI models (if scikit-learn available)
echo 🔒 Security features (if cryptography available)
echo.

REM Open application in browser after delay
timeout /t 10 /nobreak >nul
start http://localhost:3000

:end
echo Application is running. Keep this window open.
echo Press Ctrl+C to stop the servers.
pause
