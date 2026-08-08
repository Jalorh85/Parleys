@echo off
setlocal enabledelayedexpansion
title PARLEYS AI - Build y Deploy

echo.
echo =====================================================
echo   PARLEYS AI - Build y Deploy a Netlify
echo =====================================================
echo.

:: ---- CONFIGURACION ----
:: Cambia esto por el nombre de tu site en Netlify
set NETLIFY_SITE="parleys-ai"

:: ---- PASO 1: Verificar que Netlify CLI está instalado ----
echo [1/4] Verificando Netlify CLI...
netlify --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Netlify CLI no encontrado. Instalando...
    npm install -g netlify-cli
    if errorlevel 1 (
        echo  [ERROR] No se pudo instalar Netlify CLI. Instala Node.js primero.
        pause
        exit /b 1
    )
    echo  [OK] Netlify CLI instalado.
) else (
    echo  [OK] Netlify CLI listo.
)

:: ---- PASO 2: Instalar dependencias del frontend ----
echo.
echo [2/4] Instalando dependencias del frontend...
cd /d "%~dp0frontend"
call npm install --silent
if errorlevel 1 (
    echo  [ERROR] Fallo al instalar dependencias.
    pause
    exit /b 1
)
echo  [OK] Dependencias listas.

:: ---- PASO 3: Construir el frontend (Vite build) ----
echo.
echo [3/4] Construyendo el dashboard (npm run build)...
call npm run build
if errorlevel 1 (
    echo  [ERROR] El build falló. Revisa los errores de arriba.
    pause
    exit /b 1
)
echo  [OK] Build completado. Archivos en /dist

:: ---- PASO 4: Deploy a Netlify ----
echo.
echo [4/4] Subiendo a Netlify...
cd /d "%~dp0"
netlify deploy --dir=frontend/dist --prod --site=%NETLIFY_SITE%
if errorlevel 1 (
    echo.
    echo  [!] Si es el primer deploy, ejecuta primero: netlify login
    echo  [!] Luego vuelve a correr este script.
    pause
    exit /b 1
)

echo.
echo =====================================================
echo   ✓ Deploy completado exitosamente!
echo   Visita tu dashboard en: https://%NETLIFY_SITE%.netlify.app
echo =====================================================
echo.
pause
