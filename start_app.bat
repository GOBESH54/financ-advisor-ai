@echo off
echo Starting Personal Finance Advisor...
echo.

REM Start Backend Server
echo Starting Backend Server on http://localhost:5000
cd /d "%~dp0backend"
start "Backend Server" cmd /k "python app.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start Frontend Server
echo Starting Frontend Server on http://localhost:3000
cd /d "%~dp0frontend"
start "Frontend Server" cmd /k "npm start"

REM Wait a moment for frontend to start
timeout /t 5 /nobreak >nul

REM Open browser
echo Opening application in browser...
start http://localhost:3000

echo.
echo Both servers are starting...
echo Backend: http://localhost:5000
echo Frontend: http://localhost:3000
echo.
echo Press any key to exit...
pause >nul