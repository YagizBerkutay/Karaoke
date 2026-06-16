"""
transcriber.py — Söz Tanıma ve Zaman Damgalama Motoru
faster-whisper kullanarak ses dosyasından kelime bazlı zaman damgalı
söz listesi üretir.
"""

import os
from typing import Callable, Optional, List, Dict, Any


from src.engine.interfaces import ITranscriber


class Transcriber(ITranscriber):
    """
    faster-whisper ile kelime düzeyinde transkripsiyon.
    
    Çıktı formatı:
        [
            {"word": "merhaba", "start": 0.42, "end": 0.81, "score": 0.95},
            ...
        ]
    """

    def __init__(
        self,
        model_size: str = "medium",
        language: Optional[str] = None,
        on_progress: Optional[Callable[[float], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
    ):
        self.model_size = model_size
        self.language = language  # None = otomatik tespit
        self.on_progress = on_progress or (lambda p: None)
        self.on_log = on_log or (lambda m, l="info": None)

    def _log(self, msg: str, level: str = "info"):
        self.on_log(msg, level)

    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Ses dosyasını transkribe eder ve kelime listesi döner.
        
        Args:
            audio_path: vocals.wav dosya yolu
            
        Returns:
            Kelime bilgisi içeren sözlük listesi
        """
        import torch
        from faster_whisper import WhisperModel

        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        self._log(
            f"faster-whisper '{self.model_size}' modeli yükleniyor "
            f"({device.upper()}, {compute_type})...",
            "info"
        )
        self.on_progress(0.1)

        # Model yükle
        model = WhisperModel(
            self.model_size,
            device=device,
            compute_type=compute_type,
        )

        self._log("Model yüklendi. Transkripsiyon başlıyor...", "info")
        self.on_progress(0.2)

        # Transkripsiyon ayarları
        transcribe_kwargs = {
            "word_timestamps": True,      # Kelime bazlı zaman damgası
            "vad_filter": True,           # Sessiz bölgeleri atla (VAD)
            "vad_parameters": {
                "min_silence_duration_ms": 500,
            },
            "beam_size": 5,
            "best_of": 5,
            "temperature": 0.0,           # Deterministik çıktı
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": True,
        }

        if self.language:
            transcribe_kwargs["language"] = self.language
            self._log(f"Dil: {self.language}", "info")
        else:
            self._log("Dil: Otomatik tespit", "info")

        # Transkribe et
        segments, info = model.transcribe(audio_path, **transcribe_kwargs)

        detected_lang = info.language
        self._log(
            f"Tespit edilen dil: {detected_lang} "
            f"(güven: {info.language_probability:.1%})",
            "info"
        )
        self.on_progress(0.3)

        # Segment ve kelimeleri topla
        words = []
        segment_list = list(segments)  # Generator'ı tüket

        total_segs = max(len(segment_list), 1)
        for seg_idx, segment in enumerate(segment_list):
            progress = 0.3 + (seg_idx / total_segs) * 0.65
            self.on_progress(min(progress, 0.95))

            if segment.words is None:
                continue

            for word in segment.words:
                # Geçersiz zaman damgalarını filtrele
                if word.start is None or word.end is None:
                    continue
                if word.end <= word.start:
                    continue

                cleaned = word.word.strip()
                if not cleaned:
                    continue

                words.append({
                    "word":  cleaned,
                    "start": round(word.start, 3),
                    "end":   round(word.end, 3),
                    "score": round(getattr(word, "probability", 0.9), 3),
                })

        self._log(f"Toplam {len(words)} kelime tespit edildi.", "success")

        # İstatistikler
        if words:
            total_dur = words[-1]["end"] - words[0]["start"]
            wpm = len(words) / (total_dur / 60) if total_dur > 0 else 0
            self._log(f"Şarkı süresi: {total_dur:.1f}s | WPM: {wpm:.0f}", "info")

        self.on_progress(1.0)
        return words
