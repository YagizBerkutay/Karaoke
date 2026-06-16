# -*- coding: utf-8 -*-
"""
pipeline.py — Karaoke İş Akışı Koordinatörü (Pipeline)
SOLID'in Tek Sorumluluk Prensibi (SRP) gereği, tüm iş akışı koordinasyonu
arayüz sınıfından buraya taşınmıştır. Dependency Injection ile motorları kabul eder.
"""

import os
from typing import Callable, Optional, Dict, Tuple
from pathlib import Path

from src.engine.interfaces import IAudioSeparator, ITranscriber, ISubtitleGenerator, IVideoRenderer
from src.utils.temp_manager import TempManager


class PipelineCancelledException(Exception):
    """Kullanıcı işlemi iptal ettiğinde fırlatılan özel istisna."""
    pass


class KaraokePipeline:
    """Ses ayrıştırma, söz tanıma, altyazı üretme ve video render adımlarını birleştiren boru hattı."""

    def __init__(
        self,
        separator: IAudioSeparator,
        transcriber: ITranscriber,
        sub_gen: ISubtitleGenerator,
        renderer: IVideoRenderer,
        on_log: Optional[Callable[[str, str], None]] = None
    ):
        self.separator = separator
        self.transcriber = transcriber
        self.sub_gen = sub_gen
        self.renderer = renderer
        
        self.on_log = on_log or (lambda m, l="info": None)
        self._is_cancelled = False
        
        # UI güncellemeleri için callback tanımları (Observer Pattern)
        self.on_step_start = lambda idx, name: None
        self.on_step_progress = lambda idx, val: None
        self.on_step_done = lambda idx: None

    def cancel(self):
        """İşlemi iptal eder."""
        self._is_cancelled = True
        self.on_log("İşlem iptal ediliyor...", "warning")

    def check_cancelled(self):
        """İptal durumunu kontrol eder, aktifse istisna fırlatır."""
        if self._is_cancelled:
            raise PipelineCancelledException("İşlem kullanıcı tarafından iptal edildi.")

    def run(self, mp3_path: str, output_dir: str) -> Dict[str, str]:
        """Tüm boru hattını çalıştırır ve oluşturulan dosya yollarını döner."""
        self._is_cancelled = False
        temp = TempManager()
        
        try:
            # ── Adım 1: Ses Ayrıştırma ──────────────────────────────────────
            self.check_cancelled()
            self.on_step_start(0, "Ses Ayrıştırma")
            
            # Motorun kendi log/progress callbacks bağlantılarını ayarla
            if hasattr(self.separator, "on_progress"):
                self.separator.on_progress = lambda p: self.on_step_progress(0, p)
            if hasattr(self.separator, "on_log"):
                self.separator.on_log = self.on_log

            vocals_path, accomp_path = self.separator.separate(mp3_path, temp.dir)
            self.check_cancelled()
            self.on_step_done(0)
            self.on_log("Ayrıştırma tamamlandı: vocals.wav + accompaniment.wav", "success")

            # ── Adım 2: Transkripsiyon ───────────────────────────────────────
            self.check_cancelled()
            self.on_step_start(1, "Söz Tanıma")
            
            if hasattr(self.transcriber, "on_progress"):
                self.transcriber.on_progress = lambda p: self.on_step_progress(1, p)
            if hasattr(self.transcriber, "on_log"):
                self.transcriber.on_log = self.on_log

            words = self.transcriber.transcribe(vocals_path)
            self.check_cancelled()
            
            if not words:
                raise ValueError("Söz tespit edilemedi. Farklı bir model deneyin.")
                
            self.on_step_done(1)
            self.on_log(f"Söz tanıma tamamlandı: {len(words)} kelime bulundu.", "success")

            # JSON kelime zamanlamalarını kaydet
            song_name = Path(mp3_path).name.rsplit(".", 1)[0]
            words_json_path = os.path.join(output_dir, song_name + "_words.json")
            import json
            try:
                with open(words_json_path, "w", encoding="utf-8") as f:
                    json.dump(words, f, ensure_ascii=False, indent=4)
                self.on_log(f"Kelime zamanlamaları kaydedildi: {song_name}_words.json", "info")
            except Exception as e:
                self.on_log(f"Kelime zamanlamaları kaydedilemedi: {e}", "warning")

            # ── Adım 3: Altyazı Üretme ───────────────────────────────────────
            self.check_cancelled()
            self.on_step_start(2, "Altyazı Üretme")
            
            if hasattr(self.sub_gen, "on_log"):
                self.sub_gen.on_log = self.on_log
                
            ass_path = temp.path("karaoke.ass")
            self.sub_gen.generate(words, ass_path)
            
            lrc_path = os.path.join(output_dir, Path(mp3_path).name.rsplit(".", 1)[0] + ".lrc")
            self.sub_gen.generate_lrc(words, lrc_path)
            
            self.check_cancelled()
            self.on_step_done(2)
            self.on_log("Altyazı oluşturuldu (.ass + .lrc)", "success")

            # ── Adım 4: Video Render ─────────────────────────────────────────
            self.check_cancelled()
            self.on_step_start(3, "Video Render")
            
            if hasattr(self.renderer, "on_progress"):
                self.renderer.on_progress = lambda p: self.on_step_progress(3, p)
            if hasattr(self.renderer, "on_log"):
                self.renderer.on_log = self.on_log

            output_path = os.path.join(output_dir, Path(mp3_path).name.rsplit(".", 1)[0] + "_karaoke.mp4")
            
            # Renderer'a cancellation callback'ini geçiyoruz
            if hasattr(self.renderer, "render_with_cancel"):
                self.renderer.render_with_cancel(accomp_path, ass_path, output_path, self.check_cancelled)
            else:
                self.renderer.render(accomp_path, ass_path, output_path)
                
            self.on_step_done(3)
            
            return {"video": output_path, "lrc": lrc_path}
            
        except PipelineCancelledException as ce:
            self.on_log("İşlem iptal edildi.", "warning")
            raise ce
        finally:
            temp.cleanup()

    def run_from_words(self, words: list, accomp_path: str, output_path: str, ass_path: str, lrc_path: str) -> None:
        """Kelimelerden doğrudan karaoke videosu üretir (Ses ayrıştırma ve söz tanımayı atlar)."""
        self._is_cancelled = False
        
        try:
            # ── Adım 3: Altyazı Üretme ───────────────────────────────────────
            self.check_cancelled()
            self.on_step_start(2, "Altyazı Üretme")
            
            if hasattr(self.sub_gen, "on_log"):
                self.sub_gen.on_log = self.on_log
                
            self.sub_gen.generate(words, ass_path)
            self.sub_gen.generate_lrc(words, lrc_path)
            
            self.check_cancelled()
            self.on_step_done(2)
            self.on_log("Altyazı oluşturuldu (.ass + .lrc)", "success")

            # ── Adım 4: Video Render ─────────────────────────────────────────
            self.check_cancelled()
            self.on_step_start(3, "Video Render")
            
            if hasattr(self.renderer, "on_progress"):
                self.renderer.on_progress = lambda p: self.on_step_progress(3, p)
            if hasattr(self.renderer, "on_log"):
                self.renderer.on_log = self.on_log

            # Renderer'a cancellation callback'ini geçiyoruz
            if hasattr(self.renderer, "render_with_cancel"):
                self.renderer.render_with_cancel(accomp_path, ass_path, output_path, self.check_cancelled)
            else:
                self.renderer.render(accomp_path, ass_path, output_path)
                
            self.on_step_done(3)
            self.on_log("Video başarıyla oluşturuldu!", "success")
            
        except PipelineCancelledException as ce:
            self.on_log("İşlem iptal edildi.", "warning")
            raise ce
