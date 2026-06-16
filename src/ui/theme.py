"""
theme.py — Karaoke Uygulması Tema Tanımları
Renk paleti, font stilleri ve UI sabitleri.
"""

# ─── Renk Paleti ─────────────────────────────────────────────────────────────

COLORS = {
    # Arka planlar
    "bg_primary":     "#0D0D14",   # Ana arka plan — koyu lacivert siyah
    "bg_secondary":   "#13131E",   # Kart/panel arka planı
    "bg_tertiary":    "#1A1A2E",   # Hover / aktif panel
    "bg_card":        "#16162A",   # Bileşen kartları
    "bg_input":       "#0F0F1A",   # Input alanları

    # Vurgular — lila/mor gradyan
    "accent_primary":   "#A855F7",  # Ana vurgu — lila
    "accent_secondary": "#7C3AED",  # İkincil vurgu — mor
    "accent_glow":      "#C084FC",  # Parlama rengi
    "accent_active":    "#D946EF",  # Aktif karaoke highlight

    # Metin renkleri
    "text_primary":   "#F8F8FF",   # Ana metin — neredeyse beyaz
    "text_secondary": "#A0A0C0",   # İkincil metin — gri-mor
    "text_muted":     "#5A5A7A",   # Soluk metin

    # Durum renkleri
    "success":        "#10B981",   # Yeşil — tamamlandı
    "warning":        "#F59E0B",   # Sarı — uyarı
    "error":          "#EF4444",   # Kırmızı — hata
    "info":           "#3B82F6",   # Mavi — bilgi

    # İlerleme çubuğu
    "progress_bg":    "#1E1E32",
    "progress_fill":  "#A855F7",
    "progress_glow":  "#C084FC",

    # Kenarlıklar
    "border":         "#2A2A45",
    "border_focus":   "#A855F7",
}

# ─── Font Tanımları ──────────────────────────────────────────────────────────

FONTS = {
    "title":       ("Segoe UI", 28, "bold"),
    "subtitle":    ("Segoe UI", 16, "normal"),
    "heading":     ("Segoe UI", 14, "bold"),
    "body":        ("Segoe UI", 12, "normal"),
    "body_bold":   ("Segoe UI", 12, "bold"),
    "small":       ("Segoe UI", 10, "normal"),
    "caption":     ("Segoe UI", 9, "normal"),
    "mono":        ("Consolas", 10, "normal"),
    "log":         ("Consolas", 9, "normal"),
}

# ─── Boyut ve Aralık Sabitleri ────────────────────────────────────────────────

SIZES = {
    "window_width":     960,
    "window_height":    720,
    "min_width":        800,
    "min_height":       600,
    "corner_radius":    12,
    "btn_corner":       8,
    "padding_sm":       8,
    "padding_md":       16,
    "padding_lg":       24,
    "padding_xl":       32,
}

# ─── Whisper Model Bilgileri ─────────────────────────────────────────────────

WHISPER_MODELS = {
    "tiny": {
        "name":       "Tiny",
        "size":       "~75 MB",
        "speed":      "⚡⚡⚡⚡⚡",
        "quality":    "★★☆☆☆",
        "description": "En hızlı, düşük doğruluk. Test için.",
        "recommended_for": "CPU (test)",
    },
    "base": {
        "name":       "Base",
        "size":       "~150 MB",
        "speed":      "⚡⚡⚡⚡",
        "quality":    "★★★☆☆",
        "description": "Hızlı, makul doğruluk. Net İngilizce için.",
        "recommended_for": "CPU",
    },
    "small": {
        "name":       "Small",
        "size":       "~480 MB",
        "speed":      "⚡⚡⚡",
        "quality":    "★★★★☆",
        "description": "İyi denge. CPU için önerilen.",
        "recommended_for": "CPU (önerilen)",
    },
    "medium": {
        "name":       "Medium",
        "size":       "~1.5 GB",
        "speed":      "⚡⚡",
        "quality":    "★★★★★",
        "description": "Yüksek doğruluk. Türkçe için ideal.",
        "recommended_for": "GPU (önerilen)",
    },
    "large-v3": {
        "name":       "Large v3",
        "size":       "~3 GB",
        "speed":      "⚡",
        "quality":    "★★★★★+",
        "description": "Maksimum kalite. En yüksek doğruluk.",
        "recommended_for": "GPU (güçlü)",
    },
}

# ─── Desteklenen Diller ──────────────────────────────────────────────────────

LANGUAGES = {
    "auto":  "🌍 Otomatik Tespit",
    "tr":    "🇹🇷 Türkçe",
    "en":    "🇺🇸 İngilizce",
    "de":    "🇩🇪 Almanca",
    "fr":    "🇫🇷 Fransızca",
    "es":    "🇪🇸 İspanyolca",
    "it":    "🇮🇹 İtalyanca",
    "ja":    "🇯🇵 Japonca",
    "ko":    "🇰🇷 Korece",
    "ar":    "🇸🇦 Arapça",
}

# ─── Video Çıktı Ayarları ────────────────────────────────────────────────────

VIDEO_SETTINGS = {
    "resolution": "1920x1080",
    "fps":        30,
    "bg_color":   "0x0D0D14",   # FFmpeg hex formatı
    "codec_video": "libx264",
    "codec_audio": "aac",
    "crf":        18,            # Kalite (0=en iyi, 51=en kötü, 18 near-lossless)
    "preset":     "fast",
}
