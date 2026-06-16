"""
audio_separator.py — Ses Ayrıştırma Motoru
Meta AI'ın Demucs (htdemucs) modelini kullanarak MP3'ü
vocals.wav ve accompaniment.wav olarak ayırır.
"""

import os
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Callable, Optional, Tuple


from src.engine.interfaces import IAudioSeparator


class AudioSeparator(IAudioSeparator):
    """
    Demucs htdemucs modeli ile ses ayrıştırma.
    
    Çıktı:
        vocals.wav       — sadece vokal
        accompaniment.wav — müzik altyapısı (drums + bass + other)
    """

    MODEL_NAME = "htdemucs"

    def __init__(
        self,
        on_progress: Optional[Callable[[float], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
    ):
        self.on_progress = on_progress or (lambda p: None)
        self.on_log = on_log or (lambda m, l="info": None)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def _log(self, msg: str, level: str = "info"):
        self.on_log(msg, level)

    def separate(self, audio_path: str, output_dir: str) -> Tuple[str, str]:
        """
        Ses dosyasını vokale ve altyapıya ayırır.
        
        Args:
            audio_path: Giriş ses dosyası yolu (.mp3, .wav, .flac vb.)
            output_dir: Geçici çıktı klasörü
            
        Returns:
            (vocals_path, accompaniment_path) — çıktı dosya yolları
        """
        self._log(f"Cihaz: {self.device.upper()}", "info")
        self._log("Demucs htdemucs modeli yükleniyor...", "info")
        self.on_progress(0.05)

        # Modeli yükle
        from demucs.pretrained import get_model
        from demucs.apply import apply_model

        model = get_model(self.MODEL_NAME)
        model.to(self.device)
        model.eval()

        self._log("Model yüklendi. Ses dosyası okunuyor...", "info")
        self.on_progress(0.15)

        # Ses dosyasını yükle (Öncelikle pydub + FFmpeg kullan)
        try:
            self._log("Ses dosyası yükleniyor (pydub & FFmpeg)...", "info")
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            
            # Format dönüştür (Demucs 44100Hz Stereo bekler)
            if audio.frame_rate != 44100 or audio.channels != 2:
                self._log(f"Format dönüştürülüyor: {audio.frame_rate}Hz/{audio.channels}ch → 44100Hz/2ch", "info")
                audio = audio.set_frame_rate(44100).set_channels(2)
                
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples = samples.reshape((-1, 2)).T
            
            # Normalize et (pydub 16-bit için max değer 32768)
            if audio.sample_width == 2:
                samples = samples / 32768.0
            elif audio.sample_width == 4:
                samples = samples / 2147483648.0
            elif audio.sample_width == 1:
                samples = (samples - 128.0) / 128.0
                
            wav = torch.from_numpy(samples).to(self.device)
            sr = 44100
        except Exception as pydub_err:
            self._log(f"pydub ile yüklenemedi, torchaudio deneniyor: {pydub_err}", "warning")
            wav, sr = torchaudio.load(audio_path)
            wav = wav.to(self.device)

        # Stereo garantisi
        if wav.shape[0] == 1:
            wav = wav.repeat(2, 1)
        elif wav.shape[0] > 2:
            wav = wav[:2]

        # Sample rate normalizasyonu (Demucs 44100 Hz bekler)
        if sr != 44100:
            self._log(f"Sample rate dönüştürülüyor: {sr}Hz → 44100Hz", "info")
            resampler = torchaudio.transforms.Resample(sr, 44100).to(self.device)
            wav = resampler(wav)
            sr = 44100

        # Batch boyutunu ekle: [batch, channels, samples]
        wav = wav.unsqueeze(0)

        self._log("Ses ayrıştırma işlemi başladı (bu 1-5 dakika sürebilir)...", "info")
        self.on_progress(0.2)

        # Demucs uygula
        with torch.no_grad():
            sources = apply_model(
                model, wav,
                device=self.device,
                split=True,          # Bellek tasarrufu için parçalara böl
                shifts=1,            # Hafif kalite artışı
                overlap=0.25,
                progress=False,
            )

        # sources shape: [batch, stems, channels, samples]
        # stems: drums(0), bass(1), other(2), vocals(3)
        sources = sources[0]  # batch boyutunu kaldır

        stem_names = model.sources  # ['drums', 'bass', 'other', 'vocals']
        self._log(f"Ayrıştırılan ses katmanları: {stem_names}", "info")
        self.on_progress(0.8)

        # Vokal al
        vocal_idx = stem_names.index("vocals")
        vocals = sources[vocal_idx].cpu()

        # Altyapı = diğer tüm stem'lerin toplamı
        accompaniment_stems = [
            sources[i].cpu()
            for i in range(len(stem_names))
            if i != vocal_idx
        ]
        accompaniment = torch.stack(accompaniment_stems).sum(dim=0)

        # Normalize (kırpma önleme)
        vocals = self._normalize(vocals)
        accompaniment = self._normalize(accompaniment)

        self.on_progress(0.9)

        # Dosyalara kaydet
        vocals_path = os.path.join(output_dir, "vocals.wav")
        accomp_path = os.path.join(output_dir, "accompaniment.wav")

        try:
            self._log("Ses dosyaları kaydediliyor (pydub)...", "info")
            self._save_wav_with_pydub(vocals_path, vocals, sr)
            self._save_wav_with_pydub(accomp_path, accompaniment, sr)
        except Exception as save_err:
            self._log(f"pydub ile kaydedilemedi, torchaudio.save deneniyor: {save_err}", "warning")
            torchaudio.save(vocals_path, vocals, sr)
            torchaudio.save(accomp_path, accompaniment, sr)

        self._log(f"Kaydedildi: vocals.wav ({self._file_size(vocals_path)})", "success")
        self._log(f"Kaydedildi: accompaniment.wav ({self._file_size(accomp_path)})", "success")
        self.on_progress(1.0)

        return vocals_path, accomp_path

    @staticmethod
    def _save_wav_with_pydub(path: str, tensor: torch.Tensor, sample_rate: int):
        from pydub import AudioSegment
        # Clamp ve int16'ya çevir
        samples = (tensor.clamp(-1.0, 1.0).numpy() * 32767.0).astype(np.int16)
        if samples.ndim > 1:
            samples = samples.T.copy()
        
        audio_segment = AudioSegment(
            samples.tobytes(),
            frame_rate=sample_rate,
            sample_width=2,
            channels=samples.shape[1] if samples.ndim > 1 else 1
        )
        audio_segment.export(path, format="wav")

    @staticmethod
    def _normalize(audio: torch.Tensor) -> torch.Tensor:
        """Ses sinyalini [-1, 1] aralığına normalize eder."""
        peak = audio.abs().max()
        if peak > 1.0:
            audio = audio / peak * 0.95
        return audio

    @staticmethod
    def _file_size(path: str) -> str:
        size = os.path.getsize(path) / (1024 * 1024)
        return f"{size:.1f} MB"
