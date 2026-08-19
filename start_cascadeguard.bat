@echo off
title CascadeGuard AI - Startup

cd /d D:\CascadeGuard

echo ==========================================
echo       CASCADEGUARD AI COMMAND CENTER
echo ==========================================
echo.

echo [1/3] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [2/3] Starting FastAPI backend...
start "CascadeGuard FastAPI" cmd /k "cd /d D:\CascadeGuard && .venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 5000"

echo.
echo [3/3] Waiting for server...

timeout /t 5 /nobreak >nul

echo Opening CascadeGuard...
start http://127.0.0.1:5000

echo.
echo ==========================================
echo   CascadeGuard is running
echo   http://127.0.0.1:5000
echo ==========================================
echo.
pause