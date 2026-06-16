@echo off
title Karaoke Uygulamasi

if not exist "venv" (
    echo [HATA] Sanal ortam bulunamadi. Once setup.bat calistirin!
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python main.py
