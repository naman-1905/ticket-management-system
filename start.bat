@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo   Ticket Management System
echo ==========================================
echo.

echo Starting backend...
start "Ticket Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Starting frontend...
start "Ticket Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Swagger:  http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo.

endlocal