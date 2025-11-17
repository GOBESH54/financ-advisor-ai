@echo off
echo ========================================
echo Personal Finance Advisor Setup (Python 3.11)
echo ========================================

REM Check Python version
python --version | findstr "3.11"
if errorlevel 1 (
    echo Error: Python 3.11 is required but not found!
    echo Please install Python 3.11 and add it to PATH.
    pause
    exit /b 1
)

echo ✓ Python 3.11 detected

REM Create virtual environment
echo Creating virtual environment...
if exist .venv (
    echo Removing existing virtual environment...
    rmdir /s /q .venv
)

python -m venv .venv
if errorlevel 1 (
    echo Error: Failed to create virtual environment!
    pause
    exit /b 1
)

echo ✓ Virtual environment created

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements with error handling
echo Installing Python 3.11 compatible dependencies...

REM Try optimized requirements first
pip install -r requirements_optimized.txt --no-cache-dir
if errorlevel 1 (
    echo ⚠️ Some packages failed. Trying essential packages only...
    
    REM Install core packages individually
    pip install Flask==2.3.3 Flask-CORS==4.0.0 Flask-SQLAlchemy==3.0.5
    pip install pandas==2.0.3 numpy==1.26.4 scikit-learn==1.3.0
    pip install matplotlib==3.7.2 plotly==5.15.0 reportlab==4.0.4
    pip install openpyxl==3.1.2 PyPDF2==3.0.1 Pillow==10.0.1
    pip install typing-extensions==4.12.2
    
    REM Try TensorFlow (may fail on some systems)
    pip install tensorflow==2.13.0 --no-cache-dir
    if errorlevel 1 (
        echo ⚠️ TensorFlow installation failed - LSTM features will be limited
    )
    
    REM Try PyTorch (may fail on some systems)
    pip install torch==2.0.1 --no-cache-dir
    if errorlevel 1 (
        echo ⚠️ PyTorch installation failed - some AI features will be limited
    )
    
    echo ✅ Core packages installed successfully!
)

REM Create necessary directories
echo Creating project directories...
if not exist "backend\uploads" mkdir backend\uploads
if not exist "backend\reports" mkdir backend\reports
if not exist "backend\backups" mkdir backend\backups
if not exist "backend\models" mkdir backend\models
if not exist "instance" mkdir instance
if not exist "uploads" mkdir uploads
if not exist "reports" mkdir reports

REM Initialize database
echo Initializing database...
cd backend
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('✓ Database initialized')"
cd ..

echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo To start the application:
echo 1. Run: call .venv\Scripts\activate.bat
echo 2. Run: python backend\app.py
echo.
pause
