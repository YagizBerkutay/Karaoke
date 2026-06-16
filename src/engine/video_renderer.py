"""
video_renderer.py — FFmpeg Video Render Motoru
Altyapı sesi ve .ass karaoke altyazısını birleştirerek
1080p MP4 karaoke videosu üretir.
"""

import os
import subprocess
import shutil
import json
import re
from typing import Callable, Optional


class VideoRenderer:
    """
    FFmpeg tabanlı video render motoru.
    
    Özellikler:
        - 1920x1080 @ 30fps siyah arka plan
        - libass ile .ass karaoke altyazı yakma
        - H.264 + AAC çıktı
        - Gerçek zamanlı ilerleme takibi
    """

    RESOLUTION = "1920x1080"
    FPS        = 30
    BG_COLOR   = "0x0D0D14"   # Koyu lacivert siyah
    VIDEO_CODEC = "libx264"
    AUDIO_CODEC = "aac"
    CRF        = 18            # Kalite (düşük = daha iyi)
    PRESET     = "fast"        # Kodlama hızı

    def __init__(
        self,
        on_progress: Optional[Callable[[float], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
    ):
        self.on_progress = on_progress or (lambda p: None)
        self.on_log = on_log or (lambda m, l="info": None)

    def _log(self, msg: str, level: str = "info"):
        self.on_log(msg, level)

    def render(
        self,
        audio_path: str,
        subtitle_path: str,
        output_path: str,
    ) -> str:
        """
        Karaoke videosunu render eder.
        
        Args:
            audio_path:    accompaniment.wav yolu
            subtitle_path: karaoke.ass yolu
            output_path:   çıktı .mp4 yolu
            
        Returns:
            Oluşturulan video dosyası yolu
        """
        # FFmpeg kontrolü
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "FFmpeg bulunamadı! Lütfen FFmpeg'i yükleyip PATH'e ekleyin.\n"
                "İndirme: https://ffmpeg.org/download.html"
            )

        # Ses süresini al
        duration = self._get_audio_duration(audio_path)
        self._log(f"Ses süresi: {duration:.1f}s ({duration/60:.1f} dakika)", "info")
        self.on_progress(0.05)

        # FFmpeg on Windows has a hard time parsing absolute paths in the -vf filtergraph (colons/backslashes).
        # To bypass this, we copy the .ass file locally to the current working directory as a clean filename.
        temp_ass_name = "temp_karaoke_render.ass"
        shutil.copy2(subtitle_path, temp_ass_name)

        try:
            # FFmpeg komutu
            cmd = [
                "ffmpeg", "-y",                          # Üzerine yaz
                "-f", "lavfi",
                "-i", f"color=c=0x{self.BG_COLOR[2:]}:s={self.RESOLUTION}:r={self.FPS}",
                "-i", audio_path,                         # Ses girişi
                "-vf", f"ass={temp_ass_name}",            # Altyazı yakma
                "-c:v", self.VIDEO_CODEC,
                "-preset", self.PRESET,
                "-crf", str(self.CRF),
                "-c:a", self.AUDIO_CODEC,
                "-b:a", "320k",
                "-shortest",                              # Ses bitince video bitsin
                "-movflags", "+faststart",                # Web uyumluluğu
                "-progress", "pipe:1",                    # İlerleme çıktısı
                output_path,
            ]

            self._log("FFmpeg render başlatılıyor...", "info")
            self._log(f"Çözünürlük: {self.RESOLUTION} @ {self.FPS}fps", "info")
            self._log(f"Kalite: CRF={self.CRF}, Preset={self.PRESET}", "info")
            self.on_progress(0.1)

            # FFmpeg'i çalıştır ve ilerlemeyi takip et
            self._run_ffmpeg(cmd, duration)
        finally:
            # Clean up the local temporary subtitle file
            if os.path.exists(temp_ass_name):
                try:
                    os.remove(temp_ass_name)
                except Exception:
                    pass

        if not os.path.exists(output_path):
            raise RuntimeError("FFmpeg çıktı dosyası oluşturulamadı!")

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        self._log(f"Video dosyası: {size_mb:.1f} MB", "success")
        self._log(f"Çıktı: {output_path}", "success")
        self.on_progress(1.0)

        return output_path

    def _run_ffmpeg(self, cmd: list, total_duration: float):
        """FFmpeg process'i çalıştırır ve ilerlemeyi takip eder."""
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
        )

        # Stderr'i ayrı thread'de oku (bloklamayı önle)
        import threading
        stderr_lines = []

        def read_stderr():
            for line in process.stderr:
                stderr_lines.append(line.strip())

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        # Stdout'tan ilerlemeyi oku
        current_time = 0.0
        for line in process.stdout:
            line = line.strip()

            if line.startswith("out_time_ms="):
                try:
                    ms = int(line.split("=")[1])
                    current_time = ms / 1_000_000
                    if total_duration > 0:
                        progress = min(0.1 + (current_time / total_duration) * 0.88, 0.98)
                        self.on_progress(progress)

                        # Her 30 saniyede bir log
                        if int(current_time) % 30 == 0 and current_time > 0:
                            pct = (current_time / total_duration) * 100
                            self._log(
                                f"Render: {current_time:.0f}s / {total_duration:.0f}s ({pct:.0f}%)",
                                "info"
                            )
                except ValueError:
                    pass

        process.wait()
        stderr_thread.join(timeout=2)

        if process.returncode != 0:
            error_msg = "\n".join(stderr_lines[-20:])  # Son 20 satır
            raise RuntimeError(f"FFmpeg hatası (kod {process.returncode}):\n{error_msg}")

    def _get_audio_duration(self, audio_path: str) -> float:
        """FFprobe ile ses süresini saniye cinsinden alır."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    audio_path,
                ],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception:
            return 240.0  # Varsayılan: 4 dakika
