@echo off
cls
echo ========================================
echo Personal Finance Advisor - Minimal Setup
echo Python 3.11 Compatible (Core Only)
echo ========================================

REM Check Python version
python --version | findstr "3.11"
if errorlevel 1 (
    echo Error: Python 3.11 is required!
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
echo ✓ Virtual environment created

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install core packages only (no heavy AI/ML)
echo Installing core packages...

REM Essential Flask stack
pip install "Flask==2.3.3" "Flask-CORS==4.0.0" "Flask-SQLAlchemy==3.0.5"
pip install "Werkzeug==2.3.7" "SQLAlchemy>=2.0.21,<2.1"

REM Data processing (compatible versions)
pip install "numpy>=1.24.0,<1.27" "pandas>=2.0.0,<2.1"
pip install "python-dateutil==2.8.2" "pytz>=2020.1"

REM Basic ML (lightweight)
pip install "scikit-learn>=1.3.0,<1.4"

REM Visualization
pip install "matplotlib>=3.7.0,<3.8" "plotly>=5.15.0,<6.0"

REM File processing
pip install "openpyxl==3.1.2" "PyPDF2==3.0.1" "Pillow>=10.0.0,<11.0"

REM PDF processing (lightweight)
pip install "pdfplumber>=0.9.0,<1.0"

REM Reporting
pip install "reportlab>=4.0.0,<5.0"

REM Utilities
pip install "typing-extensions>=4.6.0" "python-dotenv==1.0.0" "marshmallow>=3.20.0,<4.0"

REM Caching (optional)
pip install "redis>=4.6.0,<5.0" --no-deps || echo "Redis skipped"

REM Security
pip install "cryptography>=41.0.0" --no-deps || echo "Cryptography skipped"

echo ✅ Core packages installed successfully!

REM Create directories
echo Creating project directories...
if not exist "backend\uploads" mkdir backend\uploads
if not exist "backend\reports" mkdir backend\reports
if not exist "backend\models" mkdir backend\models
if not exist "uploads" mkdir uploads
if not exist "reports" mkdir reports

REM Initialize database
echo Initializing database...
cd backend
python -c "
try:
    from flask import Flask
    from models import db
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_advisor.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
    print('✅ Database initialized')
except Exception as e:
    print('⚠️ Database init failed:', e)
    print('Will create at runtime')
"
cd ..

echo.
echo ========================================
echo ✅ Minimal Setup Complete!
echo ========================================
echo.
echo Core Features Available:
echo ✅ Flask web framework
echo ✅ Database operations
echo ✅ Bank statement upload & parsing
echo ✅ Basic transaction categorization
echo ✅ Report generation
echo ✅ Visualization (Plotly, Matplotlib)
echo.
echo AI Features (Optional - install later):
echo ⏸️ TensorFlow/LSTM forecasting
echo ⏸️ PyTorch models
echo ⏸️ Advanced transformers
echo.
echo To start the application:
echo 1. Run: start_optimized_fixed.bat
echo 2. Or: call .venv\Scripts\activate.bat && cd backend && python app.py
echo.
pause
