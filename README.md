# 🎤 Karaoke Maker

**MP3'ten Karaoke MP4 Dönüştürücü** — Tamamen ücretsiz ve açık kaynak.

Herhangi bir MP3 şarkı dosyasını otomatik olarak:
1. 🎵 Vokal ve müzik altyapısını ayırır (Demucs)
2. 🎤 Sözleri kelime bazlı zaman damgasıyla çıkarır (faster-whisper)
3. 📝 Karaoke altyazı dosyası oluşturur (.ass + .lrc)
4. 🎬 Synchronized karaoke videosuna dönüştürür (FFmpeg, 1080p)

---

## 📦 Gereksinimler

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **FFmpeg** — [ffmpeg.org](https://ffmpeg.org/download.html) (PATH'e eklenmeli)
- **NVIDIA GPU** (opsiyonel, ama çok hızlandırır)

## 🚀 Kurulum

```bash
# 1. Repoyu klonla
git clone <repo-url>
cd karaoke-maker

# 2. Kurulumu çalıştır (Windows)
setup.bat
```

Veya manuel:
```bash
python -m venv venv
venv\Scripts\activate

# GPU varsa:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
# CPU için:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt
```

## ▶️ Çalıştırma

```bash
run.bat
# veya
python main.py
```

## 🎛️ Whisper Model Seçimi

| Model | Boyut | Hız | Kalite | Önerilen |
|-------|-------|-----|--------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡⚡ | ★★ | Test |
| base | 150 MB | ⚡⚡⚡⚡ | ★★★ | CPU hızlı |
| small | 480 MB | ⚡⚡⚡ | ★★★★ | **CPU önerilen** |
| medium | 1.5 GB | ⚡⚡ | ★★★★★ | **GPU önerilen** |
| large-v3 | 3 GB | ⚡ | ★★★★★+ | Maksimum kalite |

## 🏗️ Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| UI | CustomTkinter |
| Ses Ayrıştırma | Demucs (Meta AI, htdemucs) |
| Söz Tanıma | faster-whisper (Whisper tabanlı) |
| Altyazı | ASS format + `\kf` karaoke tag |
| Video | FFmpeg + libass |

## 📁 Proje Yapısı

```
karaoke-maker/
├── main.py                    # Giriş noktası
├── requirements.txt
├── setup.bat                  # Kurulum
├── run.bat                    # Başlatma
└── src/
    ├── ui/
    │   ├── app.py             # Ana pencere
    │   ├── components.py      # UI bileşenleri
    │   └── theme.py           # Tema
    ├── engine/
    │   ├── audio_separator.py # Demucs
    │   ├── transcriber.py     # faster-whisper
    │   ├── subtitle_gen.py    # .ass üretici
    │   └── video_renderer.py  # FFmpeg
    └── utils/
        ├── temp_manager.py
        └── file_utils.py
```

## 📄 Lisans

MIT License — Ücretsiz kullanım ve dağıtım.
