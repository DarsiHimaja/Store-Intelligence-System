@echo off
title Store Intelligence API

echo.
echo =========================================
echo  Killing anything on port 8000...
echo =========================================
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo   Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo.
echo =========================================
echo  Starting API on http://localhost:8000
echo =========================================
cd /d %~dp0app
set DB_PATH=%~dp0app\store.db
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
