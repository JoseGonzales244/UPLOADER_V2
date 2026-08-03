@echo off
setlocal
cd /d "%~dp0"

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

echo Starting Interbank Plataforma Calidad Televentas (FastAPI + React Control Center)...

if exist "%VENV_PYTHON%" (
    start "" /b powershell -windowstyle hidden -Command "Start-Sleep -s 3; Start-Process 'http://localhost:8000'"
    "%VENV_PYTHON%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        start "" /b powershell -windowstyle hidden -Command "Start-Sleep -s 3; Start-Process 'http://localhost:8000'"
        py -3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
    ) else (
        start "" /b powershell -windowstyle hidden -Command "Start-Sleep -s 3; Start-Process 'http://localhost:8000'"
        python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
    )
)

if errorlevel 1 (
    echo.
    echo No se pudo iniciar el Servidor Uploader V2.
    echo Verifica que Python y las dependencias esten instaladas.
    pause
)
