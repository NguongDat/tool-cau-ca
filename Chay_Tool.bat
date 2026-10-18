@echo off
chcp 65001 > nul
title Auto Câu Cá - Bậc Thầy Câu Cá Roblox
echo =======================================================
echo    ĐANG KHỞI ĐỘNG AUTO BẬC THẦY CÂU CÁ (ROBLOX)
echo =======================================================
echo.
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo [LỖI] Không thể khởi động tool. Vui lòng kiểm tra Python đã cài đặt chưa.
    pause
)
