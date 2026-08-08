@echo off
echo ========================================================
echo   Iniciando PARLEYS AI - ML Sports Prediction Engine 2026
echo ========================================================

echo.
echo [1/2] Iniciando Servidor Backend FastAPI (Puerto 8000)...
start "PARLEYS Backend API" cmd /k "cd /d %~dp0backend && py -3 -m uvicorn app.main:app --port 8000 --reload"

timeout /t 3 /nobreak > nul

echo.
echo [2/2] Iniciando Dashboard Web React + Vite (Puerto 5173)...
start "PARLEYS Dashboard Web" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Sistema iniciado correctamente!
echo Abre tu navegador en: http://localhost:5173
echo.
pause
