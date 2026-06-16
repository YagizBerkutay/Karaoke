"""
file_utils.py — Dosya Yardımcı Araçları
"""

import os
import subprocess
from pathlib import Path


def open_file(path: str):
    """Dosyayı varsayılan uygulama ile açar (Windows)."""
    os.startfile(path)


def open_folder(path: str):
    """Klasörü Windows Gezgini'nde açar."""
    subprocess.Popen(f'explorer /select,"{path}"')


def get_safe_filename(name: str) -> str:
    """Dosya adından geçersiz karakterleri temizler."""
    invalid = r'\/:*?"<>|'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.strip()


def ensure_dir(path: str) -> str:
    """Klasör yoksa oluşturur, yolu döner."""
    os.makedirs(path, exist_ok=True)
    return path


def format_size(size_bytes: int) -> str:
    """Dosya boyutunu okunabilir formata çevirir."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """Saniyeyi MM:SS formatına çevirir."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def is_audio_file(path: str) -> bool:
    """Dosyanın desteklenen ses formatında olup olmadığını kontrol eder."""
    return Path(path).suffix.lower() in {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}
