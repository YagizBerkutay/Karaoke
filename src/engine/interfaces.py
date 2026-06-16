# -*- coding: utf-8 -*-
"""
interfaces.py — Motor bileşenleri için soyut arayüz tanımları.
SOLID'in Dependency Inversion (DIP) ve Interface Segregation (ISP) prensiplerine uygunluk sağlar.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple


class IAudioSeparator(ABC):
    """Ses ayrıştırma motoru arayüzü (Demucs)."""

    @abstractmethod
    def separate(self, audio_path: str, output_dir: str) -> Tuple[str, str]:
        """Giriş ses dosyasını vokal ve altyapı olarak ayırır."""
        pass


class ITranscriber(ABC):
    """Konuşmayı metne çevirme (söz tanıma) motoru arayüzü (Whisper)."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """Ses dosyasındaki konuşmaları kelime bazlı zaman damgalarıyla döner."""
        pass


class ISubtitleGenerator(ABC):
    """Karaoke altyazı (.ass, .lrc) üreteç arayüzü."""

    @abstractmethod
    def generate(self, words: List[Dict[str, Any]], output_path: str) -> None:
        """Kelime listesinden gelişmiş karaoke .ass dosyası oluşturur."""
        pass

    @abstractmethod
    def generate_lrc(self, words: List[Dict[str, Any]], output_path: str) -> None:
        """Kelime listesinden standart zaman damgalı .lrc dosyası oluşturur."""
        pass


class IVideoRenderer(ABC):
    """FFmpeg video render motoru arayüzü."""

    @abstractmethod
    def render(self, audio_path: str, subtitle_path: str, output_path: str) -> str:
        """Altyapı sesini ve altyazıyı birleştirerek MP4 karaoke videosu üretir."""
        pass
