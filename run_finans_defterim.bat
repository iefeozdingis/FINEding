@echo off
title FINEding - Finans Takip
cd /d "%~dp0"

:: Önce .venv'i dene
if exist "%~dp0.venv\Scripts\python.exe" (
    echo Baslatiliyor...
    "%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
    if errorlevel 1 pause
    exit /b
)

:: .venv yoksa sistem Python'unu dene
echo .venv bulunamadi, sistem Python'u deneniyor...
python "%~dp0main.py"
if errorlevel 1 (
    echo.
    echo ========================================
    echo  HATA: Python bulunamadi veya eksik!
    echo ========================================
    echo.
    echo  1. python.org adresinden Python 3.10+ indirip kurun.
    echo  2. Kurarken "Add Python to PATH" kutucugunu isaretleyin.
    echo  3. Sonra bu klasorde PowerShell acip sunlari calistirin:
    echo     python -m venv .venv
    echo     .venv\Scripts\Activate.ps1
    echo     pip install -r requirements.txt
    echo.
)
pause
