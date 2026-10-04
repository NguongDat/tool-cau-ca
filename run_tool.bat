@echo off
title Roblox Fishing Master Auto Pro
cd /d "%~dp0"
echo ==================================================
echo   Dang khoi dong Roblox Fishing Master Auto Tool...
echo ==================================================

:: 1. Check system Python
where python >nul 2>nul
if %errorlevel% equ 0 (
    python main.py
    goto end
)

:: 2. Check compiled EXE in dist folder
if exist "dist\FishingMaster_Auto_Pro\FishingMaster_Auto_Pro.exe" (
    start "" "dist\FishingMaster_Auto_Pro\FishingMaster_Auto_Pro.exe"
    goto end
)

:: 3. Check default Python 3.11 path
if exist "C:\Users\ASUS\AppData\Local\Programs\Python\Python311\python.exe" (
    "C:\Users\ASUS\AppData\Local\Programs\Python\Python311\python.exe" main.py
    goto end
)

echo.
echo [LOI] Khong tim thấy Python hoac file execute (.exe)!
echo Vui long mo thư muc 'dist\FishingMaster_Auto_Pro' va chay file .exe hoac cai dat Python.
echo.
pause

:end
