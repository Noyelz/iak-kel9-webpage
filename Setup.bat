@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0Setup.exe" (
    "%~dp0Setup.exe"
    exit /b
)
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0tools\bootstrap.py"
    exit /b
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0tools\bootstrap.py"
    exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
    python "%~dp0tools\bootstrap.py"
    exit /b
)
echo Python belum ditemukan. Pasang Python 64-bit dari python.org dan aktifkan Add Python to PATH.
pause
