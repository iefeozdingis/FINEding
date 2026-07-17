@echo off
title FINEding - Ilk Kurulum
cd /d "%~dp0"
echo.
echo ========================================
echo   FINEding - Ilk Kurulum
echo ========================================
echo.

:: Python kontrol
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi!
    echo.
    echo Lutfen python.org adresinden Python 3.10+ indirip kurun.
    echo Kurarken "Add Python to PATH" kutucugunu ISARETLEYIN!
    echo.
    pause
    exit /b 1
)
echo [OK] Python bulundu.

:: .venv olustur
if not exist "%~dp0.venv" (
    echo [*] Sanal ortam olusturuluyor...
    python -m venv .venv
    if errorlevel 1 (
        echo [HATA] Sanal ortam olusturulamadi!
        pause
        exit /b 1
    )
    echo [OK] Sanal ortam olusturuldu.
) else (
    echo [OK] Sanal ortam zaten var.
)

:: Paketleri kur
echo [*] Paketler yukleniyor...
"%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt" --quiet
if errorlevel 1 (
    echo [HATA] Paketler yuklenemedi!
    pause
    exit /b 1
)
echo [OK] Paketler yuklendi.

echo.
echo ========================================
echo   KURULUM TAMAMLANDI! 
echo ========================================
echo.
echo Uygulamayi baslatmak icin:
echo   "run_finans_defterim.bat" dosyasina cift tiklayin.
echo.
echo Ilk acilista kendi hesabinizi olusturun (Yeni Hesap Olustur).
echo Ilk kaydolan kullanici otomatik admin olur. Sifre en az 8 karakter.
echo.
pause
