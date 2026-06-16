"""
main.py — Karaoke Uygulması Giriş Noktası

Kullanım:
    python main.py

Gereksinimler:
    - Python 3.10+
    - FFmpeg (PATH'te)
    - Bağımlılıklar: pip install -r requirements.txt
      veya: setup.bat çalıştırın
"""

import sys
import os
import shutil

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def ensure_ffmpeg_in_path():
    """FFmpeg'in PATH'te olmasını garanti eder. WinGet paketlerini de kontrol eder."""
    if shutil.which("ffmpeg"):
        return True

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        winget_pkgs = os.path.join(local_appdata, "Microsoft", "WinGet", "Packages")
        if os.path.isdir(winget_pkgs):
            for item in os.listdir(winget_pkgs):
                if "FFmpeg" in item:
                    pkg_path = os.path.join(winget_pkgs, item)
                    for root, dirs, files in os.walk(pkg_path):
                        if "ffmpeg.exe" in files:
                            os.environ["PATH"] += os.pathsep + root
                            return True
    return False


ensure_ffmpeg_in_path()


def check_dependencies():
    """Kritik bağımlılıkları kontrol eder."""
    missing = []

    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")

    if missing:
        print("=" * 60)
        print("HATA: Bazı bağımlılıklar eksik!")
        print("=" * 60)
        print(f"\nEksik: {', '.join(missing)}")
        print("\nLütfen önce kurulum scriptini çalıştırın:")
        print("  setup.bat")
        print("\nVeya manuel olarak:")
        print("  pip install -r requirements.txt")
        print("=" * 60)

        # Basit hata penceresi göster
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Bağımlılık Hatası",
                f"Eksik kütüphaneler: {', '.join(missing)}\n\n"
                "Lütfen setup.bat dosyasını çalıştırın!"
            )
            root.destroy()
        except Exception:
            pass

        sys.exit(1)


def main():
    """Uygulamayı başlatır."""
    check_dependencies()

    try:
        from src.ui.app import KaraokeApp

        app = KaraokeApp()
        app.mainloop()

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"\nUygulama başlatma hatası:\n{tb}")

        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Başlatma Hatası",
                f"Uygulama başlatılamadı:\n\n{str(e)}\n\n"
                "Detaylar için konsolu kontrol edin."
            )
            root.destroy()
        except Exception:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
