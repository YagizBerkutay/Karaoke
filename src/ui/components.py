"""
components.py — Yeniden Kullanılabilir UI Bileşenleri
CustomTkinter tabanlı: StepProgress, LogPanel, ModelSelector, FileDropZone
"""

import customtkinter as ctk
from tkinter import filedialog
import threading
from src.ui.theme import COLORS, FONTS, SIZES, WHISPER_MODELS, LANGUAGES


# ─── Step Progress Bileşeni ──────────────────────────────────────────────────

class StepProgressBar(ctk.CTkFrame):
    """4 adımlı işlem ilerleme paneli."""

    STEPS = [
        ("🎵", "Ses Ayrıştırma",   "Demucs ile vokal/altyapı ayrımı"),
        ("🎤", "Söz Tanıma",       "faster-whisper ile kelime tespiti"),
        ("📝", "Altyazı Üretme",   ".ass karaoke altyazı oluşturma"),
        ("🎬", "Video Render",     "FFmpeg ile MP4 oluşturma"),
    ]

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_secondary"],
                         corner_radius=SIZES["corner_radius"], **kwargs)
        self.step_widgets = []
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(self, text="İşlem Adımları",
                             font=ctk.CTkFont(*FONTS["heading"]),
                             text_color=COLORS["text_secondary"])
        title.grid(row=0, column=0, sticky="w", padx=SIZES["padding_md"],
                   pady=(SIZES["padding_md"], 8))

        for i, (icon, name, desc) in enumerate(self.STEPS):
            frame = self._create_step(i, icon, name, desc)
            frame.grid(row=i + 1, column=0, sticky="ew",
                       padx=SIZES["padding_md"], pady=4)
            self.step_widgets.append(frame)

        # Alt dolgu
        ctk.CTkFrame(self, fg_color="transparent", height=8).grid(
            row=len(self.STEPS) + 1, column=0)

    def _create_step(self, index, icon, name, desc):
        frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"],
                             corner_radius=8)
        frame.grid_columnconfigure(1, weight=1)

        # Numaralı ikon daire
        num_label = ctk.CTkLabel(frame, text=icon,
                                 font=ctk.CTkFont(size=20),
                                 width=44, height=44,
                                 fg_color=COLORS["bg_tertiary"],
                                 corner_radius=22,
                                 text_color=COLORS["text_muted"])
        num_label.grid(row=0, column=0, rowspan=2, padx=(12, 8), pady=10)

        # İsim
        name_label = ctk.CTkLabel(frame, text=name,
                                  font=ctk.CTkFont(*FONTS["body_bold"]),
                                  text_color=COLORS["text_secondary"],
                                  anchor="w")
        name_label.grid(row=0, column=1, sticky="sw", padx=4, pady=(10, 0))

        # Açıklama
        desc_label = ctk.CTkLabel(frame, text=desc,
                                  font=ctk.CTkFont(*FONTS["caption"]),
                                  text_color=COLORS["text_muted"],
                                  anchor="w")
        desc_label.grid(row=1, column=1, sticky="nw", padx=4, pady=(0, 10))

        # İlerleme çubuğu (başlangıçta gizli)
        progress = ctk.CTkProgressBar(frame, width=120, height=4,
                                      fg_color=COLORS["progress_bg"],
                                      progress_color=COLORS["progress_fill"],
                                      corner_radius=2)
        progress.set(0)

        # Durum etiketi
        status_label = ctk.CTkLabel(frame, text="Bekliyor",
                                    font=ctk.CTkFont(*FONTS["caption"]),
                                    text_color=COLORS["text_muted"],
                                    width=80)
        status_label.grid(row=0, column=2, rowspan=2, padx=(0, 12))

        frame._icon_label = num_label
        frame._name_label = name_label
        frame._progress = progress
        frame._status_label = status_label
        frame._progress_shown = False
        return frame

    def set_step_state(self, step_index: int, state: str, progress: float = 0.0):
        """
        state: 'waiting' | 'running' | 'done' | 'error'
        progress: 0.0 - 1.0
        """
        if step_index >= len(self.step_widgets):
            return

        frame = self.step_widgets[step_index]
        icon_label = frame._icon_label
        name_label = frame._name_label
        status_label = frame._status_label
        prog_bar = frame._progress

        if state == "running":
            frame.configure(fg_color=COLORS["bg_tertiary"])
            icon_label.configure(fg_color=COLORS["accent_secondary"],
                                 text_color=COLORS["text_primary"])
            name_label.configure(text_color=COLORS["accent_glow"])
            status_label.configure(text="İşleniyor...",
                                   text_color=COLORS["accent_primary"])
            # İlerleme çubuğunu göster
            if not frame._progress_shown:
                prog_bar.grid(row=2, column=0, columnspan=3,
                              padx=12, pady=(0, 8), sticky="ew")
                frame._progress_shown = True
            prog_bar.set(progress)

        elif state == "done":
            frame.configure(fg_color=COLORS["bg_card"])
            icon_label.configure(fg_color=COLORS["success"],
                                 text_color="white", text="✓")
            name_label.configure(text_color=COLORS["text_primary"])
            status_label.configure(text="Tamamlandı ✓",
                                   text_color=COLORS["success"])
            prog_bar.set(1.0)
            prog_bar.configure(progress_color=COLORS["success"])

        elif state == "error":
            frame.configure(fg_color="#1A0000")
            icon_label.configure(fg_color=COLORS["error"],
                                 text_color="white", text="✗")
            name_label.configure(text_color=COLORS["error"])
            status_label.configure(text="Hata!",
                                   text_color=COLORS["error"])

        elif state == "waiting":
            frame.configure(fg_color=COLORS["bg_card"])
            icon_label.configure(fg_color=COLORS["bg_tertiary"],
                                 text_color=COLORS["text_muted"])
            name_label.configure(text_color=COLORS["text_secondary"])
            status_label.configure(text="Bekliyor",
                                   text_color=COLORS["text_muted"])

    def update_progress(self, step_index: int, value: float):
        if step_index < len(self.step_widgets):
            self.step_widgets[step_index]._progress.set(value)

    def reset_all(self):
        for i in range(len(self.step_widgets)):
            self.set_step_state(i, "waiting")


# ─── Log Paneli ──────────────────────────────────────────────────────────────

class LogPanel(ctk.CTkFrame):
    """Kaydırılabilir log/konsol çıktı paneli."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_primary"],
                         corner_radius=SIZES["corner_radius"], **kwargs)
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"],
                              corner_radius=8, height=36)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="📋  Konsol Çıktısı",
                     font=ctk.CTkFont(*FONTS["small"]),
                     text_color=COLORS["text_muted"]).grid(
            row=0, column=0, sticky="w", padx=12, pady=6)

        clear_btn = ctk.CTkButton(header, text="Temizle", width=70, height=24,
                                  font=ctk.CTkFont(*FONTS["caption"]),
                                  fg_color="transparent",
                                  hover_color=COLORS["bg_tertiary"],
                                  text_color=COLORS["text_muted"],
                                  command=self.clear)
        clear_btn.grid(row=0, column=1, padx=8, pady=4)

        self.textbox = ctk.CTkTextbox(self, font=ctk.CTkFont(*FONTS["log"]),
                                      fg_color=COLORS["bg_primary"],
                                      text_color=COLORS["text_secondary"],
                                      border_width=0, wrap="word",
                                      state="disabled")
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    def log(self, message: str, level: str = "info"):
        colors = {
            "info":    COLORS["text_secondary"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error":   COLORS["error"],
            "accent":  COLORS["accent_primary"],
        }
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")

        self.textbox.configure(state="normal")
        prefix = {"info": "  ", "success": "✓ ", "warning": "⚠ ",
                  "error": "✗ ", "accent": "► "}
        self.textbox.insert("end", f"[{ts}] {prefix.get(level, '')}{message}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")


# ─── Model Seçici Paneli ─────────────────────────────────────────────────────

class ModelSelector(ctk.CTkFrame):
    """Whisper model seçimi için interaktif kart paneli."""

    def __init__(self, master, default_model="medium", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.selected_model = ctk.StringVar(value=default_model)
        self._build()

    def _build(self):
        self.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        ctk.CTkLabel(self, text="Whisper AI Modeli",
                     font=ctk.CTkFont(*FONTS["heading"]),
                     text_color=COLORS["text_primary"]).grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))

        for col, (key, info) in enumerate(WHISPER_MODELS.items()):
            self._create_model_card(col, key, info)

    def _create_model_card(self, col, key, info):
        is_recommended = info["recommended_for"] in ("GPU (önerilen)", "CPU (önerilen)")

        frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"],
                             corner_radius=10,
                             border_width=2,
                             border_color=COLORS["border"])
        frame.grid(row=1, column=col, padx=4, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        # Öneri rozeti
        if is_recommended:
            badge = ctk.CTkLabel(frame, text="★ Önerilen",
                                 font=ctk.CTkFont(*FONTS["caption"]),
                                 fg_color=COLORS["accent_secondary"],
                                 corner_radius=4,
                                 text_color="white")
            badge.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        else:
            ctk.CTkFrame(frame, fg_color="transparent", height=8).grid(
                row=0, column=0)

        # Model adı
        ctk.CTkLabel(frame, text=info["name"],
                     font=ctk.CTkFont(*FONTS["heading"]),
                     text_color=COLORS["text_primary"]).grid(
            row=1, column=0, pady=(8, 2))

        # Boyut
        ctk.CTkLabel(frame, text=info["size"],
                     font=ctk.CTkFont(*FONTS["caption"]),
                     text_color=COLORS["accent_primary"]).grid(row=2, column=0)

        # Hız göstergesi
        ctk.CTkLabel(frame, text=info["speed"],
                     font=ctk.CTkFont(size=9),
                     text_color=COLORS["warning"]).grid(row=3, column=0, pady=2)

        # Kalite
        ctk.CTkLabel(frame, text=info["quality"],
                     font=ctk.CTkFont(size=9),
                     text_color=COLORS["success"]).grid(row=4, column=0)

        # Açıklama
        ctk.CTkLabel(frame, text=info["description"],
                     font=ctk.CTkFont(*FONTS["caption"]),
                     text_color=COLORS["text_muted"],
                     wraplength=100).grid(row=5, column=0, padx=6, pady=(4, 8))

        # Radio butonu
        radio = ctk.CTkRadioButton(frame, text="",
                                   variable=self.selected_model, value=key,
                                   fg_color=COLORS["accent_primary"],
                                   hover_color=COLORS["accent_secondary"],
                                   command=lambda f=frame, k=key: self._on_select(f, k))
        radio.grid(row=6, column=0, pady=(0, 10))

        frame._key = key
        frame._radio = radio
        frame.bind("<Button-1>", lambda e, f=frame, k=key: self._on_select(f, k))

        # Başlangıç seçimi
        if key == self.selected_model.get():
            self._highlight_frame(frame)

    def _on_select(self, selected_frame, key):
        self.selected_model.set(key)
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkFrame) and hasattr(child, "_key"):
                child.configure(border_color=COLORS["border"])
        self._highlight_frame(selected_frame)

    def _highlight_frame(self, frame):
        frame.configure(border_color=COLORS["accent_primary"])

    def get(self) -> str:
        return self.selected_model.get()


# ─── Dosya Sürükle-Bırak Bölgesi ─────────────────────────────────────────────

class FileDropZone(ctk.CTkFrame):
    """MP3 dosya seçimi için sürükle-bırak + tıkla bölgesi."""

    def __init__(self, master, on_file_selected=None, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_secondary"],
                         corner_radius=SIZES["corner_radius"],
                         border_width=2, border_color=COLORS["border"],
                         **kwargs)
        self.on_file_selected = on_file_selected
        self.selected_file = None
        self._build()
        self._setup_drag_drop()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, padx=24, pady=32)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.icon_label = ctk.CTkLabel(self.main_frame, text="🎵",
                                       font=ctk.CTkFont(size=48))
        self.icon_label.grid(row=0, column=0, pady=(0, 12))

        self.title_label = ctk.CTkLabel(self.main_frame,
                                        text="MP3 Dosyasını Buraya Sürükleyin",
                                        font=ctk.CTkFont(*FONTS["heading"]),
                                        text_color=COLORS["text_primary"])
        self.title_label.grid(row=1, column=0)

        self.sub_label = ctk.CTkLabel(self.main_frame,
                                      text="veya aşağıdaki butona tıklayın",
                                      font=ctk.CTkFont(*FONTS["body"]),
                                      text_color=COLORS["text_muted"])
        self.sub_label.grid(row=2, column=0, pady=(4, 16))

        self.browse_btn = ctk.CTkButton(self.main_frame, text="📂  Dosya Seç",
                                        width=180, height=44,
                                        font=ctk.CTkFont(*FONTS["body_bold"]),
                                        fg_color=COLORS["accent_secondary"],
                                        hover_color=COLORS["accent_primary"],
                                        corner_radius=SIZES["btn_corner"],
                                        command=self._browse_file)
        self.browse_btn.grid(row=3, column=0)

        self.file_info_label = ctk.CTkLabel(self.main_frame, text="",
                                            font=ctk.CTkFont(*FONTS["small"]),
                                            text_color=COLORS["accent_glow"])
        self.file_info_label.grid(row=4, column=0, pady=(12, 0))

        # Hover efekti
        for widget in [self, self.main_frame, self.icon_label,
                        self.title_label, self.sub_label]:
            widget.bind("<Enter>", lambda e: self._on_hover(True))
            widget.bind("<Leave>", lambda e: self._on_hover(False))
            widget.bind("<Button-1>", lambda e: self._browse_file())


    def _setup_drag_drop(self):
        """tkinterdnd2 ile sürükle-bırak desteği."""
        try:
            self.drop_target_register("DND_Files")
            self.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass  # tkinterdnd2 yoksa sessizce atla

    def _on_drop(self, event):
        path = event.data.strip("{}")
        if path.lower().endswith((".mp3", ".wav", ".flac", ".m4a")):
            self._set_file(path)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="MP3 Dosyası Seç",
            filetypes=[
                ("Ses Dosyaları", "*.mp3 *.wav *.flac *.m4a *.ogg"),
                ("MP3 Dosyaları", "*.mp3"),
                ("Tüm Dosyalar", "*.*"),
            ]
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        import os
        self.selected_file = path
        filename = os.path.basename(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)

        self.icon_label.configure(text="✅")
        self.title_label.configure(text=filename,
                                   text_color=COLORS["accent_glow"])
        self.sub_label.configure(text=f"Boyut: {size_mb:.1f} MB",
                                  text_color=COLORS["text_secondary"])
        self.configure(border_color=COLORS["accent_primary"])

        if self.on_file_selected:
            self.on_file_selected(path)

    def _on_hover(self, entering: bool):
        if not self.selected_file:
            color = COLORS["border_focus"] if entering else COLORS["border"]
            self.configure(border_color=color)

    def get_file(self) -> str | None:
        return self.selected_file

    def reset(self):
        self.selected_file = None
        self.icon_label.configure(text="🎵")
        self.title_label.configure(text="MP3 Dosyasını Buraya Sürükleyin",
                                    text_color=COLORS["text_primary"])
        self.sub_label.configure(text="veya aşağıdaki butona tıklayın",
                                  text_color=COLORS["text_muted"])
        self.configure(border_color=COLORS["border"])
        self.file_info_label.configure(text="")
