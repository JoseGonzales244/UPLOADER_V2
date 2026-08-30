@echo off
setlocal
cd /d "%~dp0"

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

echo Starting Interbank Plataforma Calidad Televentas (FastAPI + React Control Center)...

if exist "%VENV_PYTHON%" (
    start "" /b powershell -windowstyle hidden -Command "for ($i=0; $i -lt 40; $i++) { try { $client = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8000); $client.Close(); Start-Process 'http://localhost:8000'; break } catch { Start-Sleep -Milliseconds 500 } }"
    "%VENV_PYTHON%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        start "" /b powershell -windowstyle hidden -Command "for ($i=0; $i -lt 40; $i++) { try { $client = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8000); $client.Close(); Start-Process 'http://localhost:8000'; break } catch { Start-Sleep -Milliseconds 500 } }"
        py -3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
    ) else (
        start "" /b powershell -windowstyle hidden -Command "for ($i=0; $i -lt 40; $i++) { try { $client = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8000); $client.Close(); Start-Process 'http://localhost:8000'; break } catch { Start-Sleep -Milliseconds 500 } }"
        python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
    )
)

if errorlevel 1 (
    echo.
    echo No se pudo iniciar el Servidor Plataforma Calidad.
    echo Verifica que Python y las dependencias esten instaladas.
    pause
)
