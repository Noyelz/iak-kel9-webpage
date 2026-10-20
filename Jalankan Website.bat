@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Jalankan Setup.exe terlebih dahulu.
    pause
    exit /b 1
)
if not exist "%~dp0.env" (
    echo File .env belum tersedia. Jalankan Setup.exe terlebih dahulu.
    pause
    exit /b 1
)
echo Buka http://localhost:8000/ setelah server siap.
echo Tekan Ctrl+C untuk menghentikan server.
"%~dp0.venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
pause
