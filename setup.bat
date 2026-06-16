@echo off
title Karaoke Uygulamasi - Kurulum
color 0A

echo.
echo ==================================================
echo         KARAOKE UYGULAMASI - KURULUM
echo         MP3'den Karaoke MP4 Uretici
echo ==================================================
echo.

:: Python kontrolu
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi! Lutfen Python 3.10+ yukleyin:
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [✓] Python bulundu.

:: FFmpeg kontrolu
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [UYARI] FFmpeg bulunamadi!
    echo FFmpeg'i yukleyip PATH'e eklemeniz gerekiyor:
    echo 1. https://ffmpeg.org/download.html adresinden indirin
    echo 2. Klasoru PATH'e ekleyin
    echo.
    echo Devam etmek istiyor musunuz? (Kurulumu tamamladiktan sonra yeniden calistirin)
    pause
)

:: Sanal ortam olusturma
if not exist "venv" (
    echo.
    echo [►] Sanal Python ortami olusturuluyor...
    python -m venv venv
    echo [✓] Sanal ortam olusturuldu.
) else (
    echo [✓] Sanal ortam zaten mevcut.
)

:: Sanal ortami aktiflestir
call venv\Scripts\activate.bat

:: pip guncelle
echo.
echo [►] pip guncelleniyor...
python -m pip install --upgrade pip --quiet

:: CUDA kontrolu
echo.
echo [►] GPU tespiti yapiliyor...
python -c "import subprocess; result = subprocess.run(['nvidia-smi'], capture_output=True, text=True); exit(0 if result.returncode == 0 else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] NVIDIA GPU tespit edildi - CUDA 12.8 versiyonu yukleniyor...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128 --quiet
    echo [✓] PyTorch CUDA kuruldu.
) else (
    echo [!] NVIDIA GPU bulunamadi - CPU versiyonu yukleniyor...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
    echo [✓] PyTorch CPU kuruldu.
)

:: Diger bagimliliklari kur
echo.
echo [►] Kutuphaneler yukleniyor...
pip install customtkinter Pillow pydub numpy requests faster-whisper demucs --quiet
echo [✓] Tum kutuphaneler yuklendi.

:: tkinterdnd2 (drag-drop icin)
pip install tkinterdnd2 --quiet 2>nul

:: Kurulum dogrulama
echo.
echo [►] Kurulum dogrulaniyor...
python -c "import customtkinter; import faster_whisper; import demucs; import torch; print('  [✓] Tum moduller basariyla yuklendi!'); print('  [✓] CUDA:', torch.cuda.is_available())"

echo.
echo ==================================================
echo   KURULUM TAMAMLANDI!
echo   Uygulamayi baslatmak icin: run.bat
echo ==================================================
echo.
pause
