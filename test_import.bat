@echo off
echo Testing Personal Finance Advisor Import Functionality...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install requests if not available
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Installing requests module...
    pip install requests
)

REM Run the test
python test_import.py

echo.
echo Test completed. Press any key to exit...
pause >nul