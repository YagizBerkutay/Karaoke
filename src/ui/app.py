"""
app.py — Karaoke Uygulması Ana Penceresi
CustomTkinter tabanlı modern dark mode masaüstü uygulaması.
"""

import customtkinter as ctk
import threading
import os
import sys
from pathlib import Path
from tkinter import filedialog, messagebox

from src.ui.theme import COLORS, FONTS, SIZES, LANGUAGES
from src.ui.components import FileDropZone, StepProgressBar, LogPanel, ModelSelector


class KaraokeApp(ctk.CTk):
    """Ana uygulama penceresi."""

    def __init__(self):
        super().__init__()
        self._configure_window()
        self._setup_ctk()
        self.original_words = []
        self.lyrics_text = ""
        self._build_ui()
        self._processing_thread = None
        self._is_processing = False
        self.pipeline = None
        self._bind_keys()

    # ─── Pencere Yapılandırması ───────────────────────────────────────────────

    def _configure_window(self):
        self.title("🎵 Karaoke Maker — MP3'ten Karaoke MP4")
        self.geometry(f"{SIZES['window_width']}x{SIZES['window_height']}")
        self.minsize(SIZES["min_width"], SIZES["min_height"])
        self.configure(fg_color=COLORS["bg_primary"])
        # Pencereyi ekran ortasına al
        self.update_idletasks()
        x = (self.winfo_screenwidth() - SIZES["window_width"]) // 2
        y = (self.winfo_screenheight() - SIZES["window_height"]) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_ctk(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

    def _bind_keys(self):
        self.bind("<Return>", lambda e: self._on_enter_pressed())
        self.bind("<Escape>", lambda e: self._cancel_processing())

    def _on_enter_pressed(self):
        if self.start_btn.cget("state") == "normal":
            self._start_processing()

    # ─── UI İnşası ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Tek kolonlu, geniş ekran yapısını geri yükle
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_main_content()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"],
                               corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        # Logo ve başlık
        logo_frame = ctk.CTkFrame(header, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=SIZES["padding_lg"],
                        pady=SIZES["padding_md"])

        ctk.CTkLabel(logo_frame, text="🎤",
                     font=ctk.CTkFont(size=32)).grid(row=0, column=0,
                                                      padx=(0, 12))
        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.grid(row=0, column=1)
        ctk.CTkLabel(title_frame, text="Karaoke Maker",
                     font=ctk.CTkFont(*FONTS["title"]),
                     text_color=COLORS["text_primary"]).grid(row=0, column=0,
                                                              sticky="w")
        ctk.CTkLabel(title_frame, text="MP3 → Karaoke MP4 Dönüştürücü",
                     font=ctk.CTkFont(*FONTS["small"]),
                     text_color=COLORS["text_muted"]).grid(row=1, column=0,
                                                            sticky="w")

        # GPU durumu
        self.gpu_label = ctk.CTkLabel(header, text="GPU: Kontrol ediliyor...",
                                       font=ctk.CTkFont(*FONTS["caption"]),
                                       text_color=COLORS["text_muted"])
        self.gpu_label.grid(row=0, column=1, padx=SIZES["padding_md"])

        # Sürüm
        ctk.CTkLabel(header, text="v1.0",
                     font=ctk.CTkFont(*FONTS["caption"]),
                     text_color=COLORS["text_muted"]).grid(
            row=0, column=2, padx=SIZES["padding_lg"])

        threading.Thread(target=self._check_gpu, daemon=True).start()

    def _check_gpu(self):
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                vram = torch.cuda.get_device_properties(0).total_memory / 1e9
                text = f"🟢 GPU: {name} ({vram:.1f} GB VRAM)"
                color = COLORS["success"]
            else:
                text = "🟡 GPU: CPU Modu (CUDA yok)"
                color = COLORS["warning"]
        except ImportError:
            text = "⚪ GPU: PyTorch yüklü değil"
            color = COLORS["text_muted"]

        self.after(0, lambda: self.gpu_label.configure(
            text=text, text_color=color))

    def _build_main_content(self):
        # ── Tam Genişlikte Tabview ──
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLORS["bg_primary"],
            segmented_button_selected_color=COLORS["accent_secondary"],
            segmented_button_selected_hover_color=COLORS["accent_primary"],
            segmented_button_unselected_color=COLORS["bg_secondary"],
            text_color=COLORS["text_primary"]
        )
        self.tabview.grid(
            row=1, column=0,
            sticky="nsew",
            padx=SIZES["padding_md"],
            pady=(0, SIZES["padding_md"])
        )
        self.tabview.configure(command=self._on_tab_changed)

        tab_auto = self.tabview.add("Otomatik Oluştur")
        tab_manual = self.tabview.add("Söz Düzenle & Render")

        # Configure tab_auto grid
        tab_auto.grid_columnconfigure(0, weight=1)
        tab_auto.grid_rowconfigure(0, weight=1)

        # Tab 1: Scrollable container for auto-gen inputs and outputs
        main = ctk.CTkScrollableFrame(tab_auto, fg_color=COLORS["bg_primary"],
                                       scrollbar_button_color=COLORS["bg_tertiary"])
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)

        # HCI: Windows'ta CTkScrollableFrame'in yavaş kayma sorununu düzelt
        original_mouse_wheel = main._mouse_wheel_all
        def new_mouse_wheel(event):
            event.delta = event.delta * 3
            original_mouse_wheel(event)
        main._mouse_wheel_all = new_mouse_wheel

        row = 0

        # ── 1. Dosya Seçimi ──
        section_lbl = ctk.CTkLabel(main, text="1.  Müzik Dosyası",
                                   font=ctk.CTkFont(*FONTS["heading"]),
                                   text_color=COLORS["accent_glow"])
        section_lbl.grid(row=row, column=0, sticky="w",
                          padx=SIZES["padding_lg"], pady=(SIZES["padding_lg"], 8))
        row += 1

        self.file_zone = FileDropZone(main, on_file_selected=self._on_file_selected,
                                      height=180)
        self.file_zone.grid(row=row, column=0, sticky="ew",
                             padx=SIZES["padding_lg"], pady=(0, SIZES["padding_lg"]))
        row += 1

        # ── 2. Model Ayarları ──
        section_lbl2 = ctk.CTkLabel(main, text="2.  Yapay Zeka Modeli",
                                    font=ctk.CTkFont(*FONTS["heading"]),
                                    text_color=COLORS["accent_glow"])
        section_lbl2.grid(row=row, column=0, sticky="w",
                           padx=SIZES["padding_lg"], pady=(0, 8))
        row += 1

        # GPU uyarısı
        self.gpu_hint = ctk.CTkLabel(
            main,
            text="💡  GPU tespit edildi — 'Medium' modeli önerilir (yüksek kalite + hızlı)",
            font=ctk.CTkFont(*FONTS["small"]),
            text_color=COLORS["success"],
            fg_color=COLORS["bg_secondary"],
            corner_radius=6,
        )
        self.gpu_hint.grid(row=row, column=0, sticky="ew",
                            padx=SIZES["padding_lg"], pady=(0, 8),
                            ipadx=12, ipady=6)
        row += 1

        model_frame = ctk.CTkFrame(main, fg_color=COLORS["bg_secondary"],
                                    corner_radius=SIZES["corner_radius"])
        model_frame.grid(row=row, column=0, sticky="ew",
                          padx=SIZES["padding_lg"], pady=(0, SIZES["padding_lg"]))
        model_frame.grid_columnconfigure(0, weight=1)

        self.model_selector = ModelSelector(model_frame, default_model="medium")
        self.model_selector.grid(row=0, column=0, sticky="ew",
                                  padx=SIZES["padding_lg"],
                                  pady=SIZES["padding_lg"])
        row += 1

        # ── 3. Dil Seçimi ──
        section_lbl3 = ctk.CTkLabel(main, text="3.  Dil Ayarları",
                                    font=ctk.CTkFont(*FONTS["heading"]),
                                    text_color=COLORS["accent_glow"])
        section_lbl3.grid(row=row, column=0, sticky="w",
                           padx=SIZES["padding_lg"], pady=(0, 8))
        row += 1

        lang_frame = ctk.CTkFrame(main, fg_color=COLORS["bg_secondary"],
                                   corner_radius=SIZES["corner_radius"])
        lang_frame.grid(row=row, column=0, sticky="ew",
                         padx=SIZES["padding_lg"], pady=(0, SIZES["padding_lg"]))
        lang_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(lang_frame, text="Şarkı Dili:",
                     font=ctk.CTkFont(*FONTS["body"]),
                     text_color=COLORS["text_secondary"]).grid(
            row=0, column=0, padx=SIZES["padding_lg"],
            pady=SIZES["padding_md"], sticky="w")

        self.lang_var = ctk.StringVar(value="auto")
        lang_options = list(LANGUAGES.values())
        lang_keys = list(LANGUAGES.keys())

        self.lang_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=lang_options,
            variable=ctk.StringVar(value=LANGUAGES["auto"]),
            width=220, height=38,
            fg_color=COLORS["bg_card"],
            button_color=COLORS["accent_secondary"],
            button_hover_color=COLORS["accent_primary"],
            dropdown_fg_color=COLORS["bg_secondary"],
            font=ctk.CTkFont(*FONTS["body"]),
            command=lambda v: self.lang_var.set(
                lang_keys[lang_options.index(v)]
            )
        )
        self.lang_menu.grid(row=0, column=1, padx=SIZES["padding_md"],
                             pady=SIZES["padding_md"], sticky="w")
        row += 1

        # ── 4. Çıktı Klasörü ──
        section_lbl4 = ctk.CTkLabel(main, text="4.  Çıktı Klasörü",
                                    font=ctk.CTkFont(*FONTS["heading"]),
                                    text_color=COLORS["accent_glow"])
        section_lbl4.grid(row=row, column=0, sticky="w",
                           padx=SIZES["padding_lg"], pady=(0, 8))
        row += 1

        output_frame = ctk.CTkFrame(main, fg_color=COLORS["bg_secondary"],
                                     corner_radius=SIZES["corner_radius"])
        output_frame.grid(row=row, column=0, sticky="ew",
                           padx=SIZES["padding_lg"],
                           pady=(0, SIZES["padding_lg"]))
        output_frame.grid_columnconfigure(0, weight=1)

        out_inner = ctk.CTkFrame(output_frame, fg_color="transparent")
        out_inner.grid(row=0, column=0, sticky="ew",
                       padx=SIZES["padding_lg"], pady=SIZES["padding_md"])
        out_inner.grid_columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(out_inner,
                                          placeholder_text="Çıktı klasörü seçin...",
                                          font=ctk.CTkFont(*FONTS["body"]),
                                          fg_color=COLORS["bg_input"],
                                          border_color=COLORS["border"],
                                          text_color=COLORS["text_primary"],
                                          height=40)
        self.output_entry.grid(row=0, column=0, sticky="ew")
        self.output_entry.bind("<KeyRelease>", lambda e: self._validate_inputs())

        ctk.CTkButton(out_inner, text="📁", width=44, height=40,
                      fg_color=COLORS["bg_tertiary"],
                      hover_color=COLORS["border"],
                      font=ctk.CTkFont(size=16),
                      command=self._browse_output).grid(
            row=0, column=1, padx=(8, 0))
        row += 1

        # ── 5. İlerleme ve Log (Otomatik Oluştur Tabı İçin Alt Kısım) ──
        bottom_frame = ctk.CTkFrame(main, fg_color="transparent")
        bottom_frame.grid(row=row, column=0, sticky="ew",
                           padx=SIZES["padding_lg"],
                           pady=(0, SIZES["padding_xl"]))
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=1)

        self.step_progress = StepProgressBar(bottom_frame)
        self.step_progress.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.log_panel = LogPanel(bottom_frame, height=280)
        self.log_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # ── Tab 2: Manual Word Editor ──
        tab_manual.grid_columnconfigure(0, weight=1)
        tab_manual.grid_rowconfigure(1, weight=0) # Button frame does not need to expand
        tab_manual.grid_rowconfigure(2, weight=1) # Log panel expands to fill the space

        # Manual File Inputs Frame
        manual_inputs = ctk.CTkFrame(tab_manual, fg_color=COLORS["bg_secondary"], corner_radius=SIZES["corner_radius"])
        manual_inputs.grid(row=0, column=0, sticky="ew", pady=(0, SIZES["padding_md"]))
        manual_inputs.grid_columnconfigure(1, weight=1)
        
        # Row 0: Word JSON file
        ctk.CTkLabel(manual_inputs, text="Kelime JSON:", font=ctk.CTkFont(*FONTS["body_bold"]), text_color=COLORS["text_secondary"]).grid(row=0, column=0, padx=SIZES["padding_md"], pady=8, sticky="w")
        self.manual_json_entry = ctk.CTkEntry(manual_inputs, placeholder_text="Kelime zamanlama JSON dosyası seçin...", font=ctk.CTkFont(*FONTS["body"]), fg_color=COLORS["bg_input"], border_color=COLORS["border"], text_color=COLORS["text_primary"], height=36)
        self.manual_json_entry.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        self.manual_json_entry.bind("<KeyRelease>", lambda e: self._validate_inputs())
        ctk.CTkButton(manual_inputs, text="📂", width=36, height=36, fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"], font=ctk.CTkFont(size=14), command=self._browse_manual_json).grid(row=0, column=2, padx=(0, SIZES["padding_md"]), pady=8)
        
        # Row 1: Accompaniment Audio file
        ctk.CTkLabel(manual_inputs, text="Altyapı Sesi:", font=ctk.CTkFont(*FONTS["body_bold"]), text_color=COLORS["text_secondary"]).grid(row=1, column=0, padx=SIZES["padding_md"], pady=8, sticky="w")
        self.manual_audio_entry = ctk.CTkEntry(manual_inputs, placeholder_text="Altyapı (accompaniment.wav) dosyası seçin...", font=ctk.CTkFont(*FONTS["body"]), fg_color=COLORS["bg_input"], border_color=COLORS["border"], text_color=COLORS["text_primary"], height=36)
        self.manual_audio_entry.grid(row=1, column=1, padx=8, pady=8, sticky="ew")
        self.manual_audio_entry.bind("<KeyRelease>", lambda e: self._validate_inputs())
        ctk.CTkButton(manual_inputs, text="📂", width=36, height=36, fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"], font=ctk.CTkFont(size=14), command=self._browse_manual_audio).grid(row=1, column=2, padx=(0, SIZES["padding_md"]), pady=8)
        
        # Row 2: Output Directory
        ctk.CTkLabel(manual_inputs, text="Çıktı Klasörü:", font=ctk.CTkFont(*FONTS["body_bold"]), text_color=COLORS["text_secondary"]).grid(row=2, column=0, padx=SIZES["padding_md"], pady=8, sticky="w")
        self.manual_output_entry = ctk.CTkEntry(manual_inputs, placeholder_text="Çıktı klasörü seçin...", font=ctk.CTkFont(*FONTS["body"]), fg_color=COLORS["bg_input"], border_color=COLORS["border"], text_color=COLORS["text_primary"], height=36)
        self.manual_output_entry.grid(row=2, column=1, padx=8, pady=8, sticky="ew")
        self.manual_output_entry.bind("<KeyRelease>", lambda e: self._validate_inputs())
        ctk.CTkButton(manual_inputs, text="📂", width=36, height=36, fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"], font=ctk.CTkFont(size=14), command=self._browse_manual_output).grid(row=2, column=2, padx=(0, SIZES["padding_md"]), pady=8)

        # Word Editor Frame
        editor_frame = ctk.CTkFrame(tab_manual, fg_color=COLORS["bg_secondary"], corner_radius=SIZES["corner_radius"])
        editor_frame.grid(row=1, column=0, sticky="ew", pady=(0, SIZES["padding_md"]))
        editor_frame.grid_columnconfigure(0, weight=1)
        
        # Button/Card to trigger Full Screen Lyrics Editor
        self.edit_lyrics_btn = ctk.CTkButton(
            editor_frame,
            text="📝 Şarkı Sözlerini Düzenle (Tam Ekran)",
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=50,
            corner_radius=SIZES["corner_radius"],
            command=self._open_lyrics_editor
        )
        self.edit_lyrics_btn.grid(row=0, column=0, sticky="ew", padx=SIZES["padding_md"], pady=(SIZES["padding_md"], 8))
        self.edit_lyrics_btn.configure(state="disabled") # Disable until JSON is loaded
        
        # Word counts status label
        self.words_count_label = ctk.CTkLabel(editor_frame, text="Kelime Sayısı: -", font=ctk.CTkFont(*FONTS["small"]), text_color=COLORS["text_muted"])
        self.words_count_label.grid(row=1, column=0, padx=SIZES["padding_md"], pady=(0, SIZES["padding_md"]), sticky="w")

        # ── Tab 2 Altı: Sadece Manuel Log Paneli (Yer kazanmak için Progress Bar kaldırıldı) ──
        self.manual_log_panel = LogPanel(tab_manual, height=180)
        self.manual_log_panel.grid(row=2, column=0, sticky="nsew", pady=(0, 0))

        # GPU hint update (async)
        threading.Thread(target=self._update_gpu_hint, daemon=True).start()

    def _update_gpu_hint(self):
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                text = f"💡  GPU tespit edildi ({name}) — 'Medium' modeli önerilir"
                color = COLORS["success"]
            else:
                text = "💡  GPU bulunamadı — CPU için 'Small' modeli önerilir"
                color = COLORS["warning"]
                self.after(0, lambda: self.model_selector.selected_model.set("small"))
        except ImportError:
            text = "⚠️  PyTorch yüklü değil — setup.bat çalıştırın"
            color = COLORS["error"]

        self.after(0, lambda: self.gpu_hint.configure(text=text,
                                                       text_color=color))

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"],
                               corner_radius=0, height=80)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)
        footer.grid_propagate(False)

        # Bilgi etiketi
        self.status_label = ctk.CTkLabel(footer, text="Dosya seçin ve başlatın",
                                          font=ctk.CTkFont(*FONTS["body"]),
                                          text_color=COLORS["text_muted"])
        self.status_label.grid(row=0, column=0, padx=SIZES["padding_lg"])

        # İptal butonu
        self.cancel_btn = ctk.CTkButton(footer, text="İptal",
                                         width=100, height=44,
                                         font=ctk.CTkFont(*FONTS["body_bold"]),
                                         fg_color=COLORS["bg_tertiary"],
                                         hover_color=COLORS["error"],
                                         text_color=COLORS["text_secondary"],
                                         state="disabled",
                                         command=self._cancel_processing)
        self.cancel_btn.grid(row=0, column=1, sticky="e",
                               padx=(0, SIZES["padding_md"]))

        # Başlat butonu
        self.start_btn = ctk.CTkButton(
            footer, text="🚀  Karaoke Videosu Oluştur",
            width=260, height=52,
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["accent_primary"],
            corner_radius=SIZES["btn_corner"],
            state="disabled",
            command=self._start_processing
        )
        self.start_btn.grid(row=0, column=2, padx=SIZES["padding_lg"])

    # ─── Olay İşleyiciler ─────────────────────────────────────────────────────

    def _on_file_selected(self, path: str):
        # Otomatik çıktı klasörü ayarla
        output_dir = str(Path(path).parent)
        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, output_dir)

        self.log_panel.log(f"Dosya yüklendi: {os.path.basename(path)}", "success")
        self.log_panel.log(f"Klasör: {output_dir}", "info")
        self._validate_inputs()

    def _browse_output(self):
        path = filedialog.askdirectory(title="Çıktı Klasörü Seç")
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)
            self._validate_inputs()

    def _browse_manual_json(self):
        path = filedialog.askopenfilename(
            title="Kelime Zamanlama JSON Dosyası Seç",
            filetypes=[
                ("JSON Dosyaları", "*.json"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        if path:
            self.manual_json_entry.delete(0, "end")
            self.manual_json_entry.insert(0, path)
            self._load_words_json(path)
            self._validate_inputs()

    def _browse_manual_audio(self):
        path = filedialog.askopenfilename(
            title="Altyapı Ses Dosyası Seç",
            filetypes=[
                ("Ses Dosyaları", "*.mp3 *.wav *.flac *.m4a *.ogg"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        if path:
            self.manual_audio_entry.delete(0, "end")
            self.manual_audio_entry.insert(0, path)
            self._validate_inputs()

    def _browse_manual_output(self):
        path = filedialog.askdirectory(title="Çıktı Klasörü Seç")
        if path:
            self.manual_output_entry.delete(0, "end")
            self.manual_output_entry.insert(0, path)
            self._validate_inputs()

    def _load_words_json(self, json_path: str):
        import json
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                self.original_words = json.load(f)
            
            if not isinstance(self.original_words, list):
                raise ValueError("JSON kök elementi bir liste olmalıdır.")
            
            # Group words into lines for display (using ASS line grouping logic)
            lines = []
            current_line = []
            for i, word_data in enumerate(self.original_words):
                if not isinstance(word_data, dict) or "word" not in word_data or "start" not in word_data or "end" not in word_data:
                    continue
                
                # Check for gap to start a new line
                if current_line and i > 0:
                    gap = word_data["start"] - self.original_words[i - 1]["end"]
                    if gap > 1.5:
                        lines.append(" ".join(current_line))
                        current_line = []
                
                current_line.append(word_data["word"])
                
                # Max 8 words per line or sentence end
                is_sentence_end = word_data["word"].rstrip().endswith((".", "!", "?", "，", "。"))
                if len(current_line) >= 8 or is_sentence_end:
                    lines.append(" ".join(current_line))
                    current_line = []
            
            if current_line:
                lines.append(" ".join(current_line))
                
            lyrics_text = "\n".join(lines)
            
            # Store in self.lyrics_text and enable the edit button
            self.lyrics_text = lyrics_text
            self.edit_lyrics_btn.configure(state="normal")
            
            self._update_word_counts()
            
            self.log_panel.log(f"JSON dosyasından {len(self.original_words)} kelime yüklendi.", "success")
            
            # Smart auto-detection of audio file and output directory
            json_dir = os.path.dirname(json_path)
            json_name = os.path.basename(json_path)
            
            # 1. Set output folder to json's folder
            if not self.manual_output_entry.get().strip():
                self.manual_output_entry.insert(0, json_dir)
                self.log_panel.log(f"Çıktı klasörü otomatik ayarlandı: {json_dir}", "info")
                
            # 2. Try to find audio in the same folder
            if not self.manual_audio_entry.get().strip():
                audio_candidates = ["accompaniment.wav", "vocals.wav"]
                prefix = json_name.replace("_words.json", "")
                audio_candidates.append(f"{prefix}_accompaniment.wav")
                audio_candidates.append(f"{prefix}.wav")
                audio_candidates.append(f"{prefix}.mp3")
                
                for candidate in audio_candidates:
                    cand_path = os.path.join(json_dir, candidate)
                    if os.path.exists(cand_path):
                        self.manual_audio_entry.insert(0, cand_path)
                        self.log_panel.log(f"Altyapı ses dosyası otomatik tespit edildi: {candidate}", "success")
                        break
                        
        except Exception as e:
            messagebox.showerror("Yükleme Hatası", f"JSON dosyası okunamadı veya biçimi geçersiz:\n{e}")

    def _update_word_counts(self, event=None):
        if not hasattr(self, "original_words") or not self.original_words:
            self.words_count_label.configure(text="Kelime Sayısı: -", text_color=COLORS["text_muted"])
            return
            
        orig_count = len(self.original_words)
        lyrics_text = self.lyrics_text.strip()
        edited_words = lyrics_text.split()
        edited_count = len(edited_words)
        
        text = f"Kelime Sayısı — Orijinal: {orig_count} | Düzenlenen: {edited_count}"
        if orig_count == edited_count:
            color = COLORS["success"]
            text += " (Zamanlamalar 1:1 eşleşiyor ✓)"
        else:
            color = COLORS["warning"]
            text += " (Farklı kelime sayısı: Zamanlamalar orantılı dağıtılacaktır ⚠)"
            
        self.words_count_label.configure(text=text, text_color=color)

    def _on_tab_changed(self):
        active_tab = self.tabview.get()
        if active_tab == "Otomatik Oluştur":
            self.start_btn.configure(text="🚀  Karaoke Videosu Oluştur")
        else:
            self.start_btn.configure(text="⚡  Videoyu Yeniden Oluştur")
        self._validate_inputs()

    def _validate_inputs(self):
        active_tab = self.tabview.get()
        
        if active_tab == "Otomatik Oluştur":
            mp3_path = self.file_zone.get_file()
            output_dir = self.output_entry.get().strip()
            
            if mp3_path and output_dir and os.path.isdir(output_dir):
                self.start_btn.configure(state="normal")
                self._set_status("Hazır — Başlatmak için butona tıklayın ✓")
            else:
                self.start_btn.configure(state="disabled")
                if not mp3_path:
                    self._set_status("Dosya seçin ve başlatın")
                else:
                    self._set_status("Geçerli bir çıktı klasörü girin")
        else:
            # Manual tab validation
            json_path = self.manual_json_entry.get().strip()
            audio_path = self.manual_audio_entry.get().strip()
            output_dir = self.manual_output_entry.get().strip()
            lyrics_text = self.lyrics_text.strip()
            
            is_valid = True
            
            # Check files and directories
            if not (json_path and os.path.isfile(json_path)):
                is_valid = False
            if not (audio_path and os.path.isfile(audio_path)):
                is_valid = False
            if not (output_dir and os.path.isdir(output_dir)):
                is_valid = False
            if not lyrics_text:
                is_valid = False
                
            if is_valid:
                self.start_btn.configure(state="normal")
                self._set_status("Hazır — Yeniden oluşturmak için tıklayın ✓")
            else:
                self.start_btn.configure(state="disabled")
                if not json_path:
                    self._set_status("JSON kelime dosyasını seçin")
                elif not audio_path:
                    self._set_status("Altyapı ses dosyasını seçin")
                elif not output_dir or not os.path.isdir(output_dir):
                    self._set_status("Geçerli bir çıktı klasörü girin")
                elif not lyrics_text:
                    self._set_status("Şarkı sözleri yüklenemedi")

    def _set_status(self, text: str):
        self.status_label.configure(text=text)

    # ─── İşlem Yönetimi ──────────────────────────────────────────────────────

    def _start_processing(self):
        active_tab = self.tabview.get()
        if active_tab == "Otomatik Oluştur":
            self._start_auto_processing()
        else:
            self._start_manual_processing()

    def _start_auto_processing(self):
        mp3_path = self.file_zone.get_file()
        output_dir = self.output_entry.get().strip()
        model = self.model_selector.get()
        language = self.lang_var.get()

        if not mp3_path or not output_dir or not os.path.isdir(output_dir):
            return

        # UI hazırlık
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.step_progress.reset_all()
        self.log_panel.clear()
        self._is_processing = True

        self.log_panel.log("═══════════════════════════════════", "info")
        self.log_panel.log("Karaoke video üretimi başlatıldı!", "accent")
        self.log_panel.log(f"Model: {model.upper()} | Dil: {language}", "info")
        self.log_panel.log("═══════════════════════════════════", "info")

        # Dependency Injection (SOLID)
        from src.engine.audio_separator import AudioSeparator
        from src.engine.transcriber import Transcriber
        from src.engine.subtitle_gen import SubtitleGenerator
        from src.engine.video_renderer import VideoRenderer
        from src.engine.pipeline import KaraokePipeline

        separator = AudioSeparator()
        transcriber = Transcriber(model_size=model, language=language if language != "auto" else None)
        sub_gen = SubtitleGenerator()
        renderer = VideoRenderer()

        self.pipeline = KaraokePipeline(
            separator=separator,
            transcriber=transcriber,
            sub_gen=sub_gen,
            renderer=renderer,
            on_log=self.log_panel.log
        )
        
        # Pipeline callbacks setup
        self.pipeline.on_step_start = self._step_start
        self.pipeline.on_step_progress = self._step_progress
        self.pipeline.on_step_done = self._step_done

        # Arkaplanda işle
        self._processing_thread = threading.Thread(
            target=self._run_pipeline,
            args=(mp3_path, output_dir),
            daemon=True
        )
        self._processing_thread.start()

    def _start_manual_processing(self):
        json_path = self.manual_json_entry.get().strip()
        audio_path = self.manual_audio_entry.get().strip()
        output_dir = self.manual_output_entry.get().strip()
        lyrics_text = self.lyrics_text.strip()
        
        if not json_path or not audio_path or not output_dir or not lyrics_text:
            return
            
        # Parse edited words
        edited_words_list = lyrics_text.split()
        if not edited_words_list:
            messagebox.showerror("Hata", "Şarkı sözleri boş olamaz.")
            return

        # Align with original timings
        words = []
        n_orig = len(self.original_words)
        n_edit = len(edited_words_list)
        
        if n_orig == n_edit:
            for ew, ow in zip(edited_words_list, self.original_words):
                words.append({
                    "word": ew,
                    "start": ow["start"],
                    "end": ow["end"],
                    "score": 1.0
                })
        else:
            # Proportional mapping (keeps silence gaps intact due to sequence matching)
            for i, ew in enumerate(edited_words_list):
                orig_idx = min(int(i * n_orig / n_edit), n_orig - 1)
                ow = self.original_words[orig_idx]
                words.append({
                    "word": ew,
                    "start": ow["start"],
                    "end": ow["end"],
                    "score": 1.0
                })

        # UI hazırlık
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.manual_log_panel.clear()
        self._is_processing = True

        json_name = os.path.basename(json_path)
        song_name = json_name.replace("_words.json", "")
        output_path = os.path.join(output_dir, song_name + "_edited_karaoke.mp4")
        
        ass_path = os.path.join(output_dir, "temp_manual_render.ass")
        lrc_path = os.path.join(output_dir, song_name + "_edited.lrc")

        self.manual_log_panel.log("═══════════════════════════════════", "info")
        self.manual_log_panel.log("Manuel Karaoke video üretimi başlatıldı!", "accent")
        self.manual_log_panel.log(f"Şarkı: {song_name} | Toplam Kelime: {len(words)}", "info")
        self.manual_log_panel.log("═══════════════════════════════════", "info")

        from src.engine.subtitle_gen import SubtitleGenerator
        from src.engine.video_renderer import VideoRenderer
        from src.engine.pipeline import KaraokePipeline

        sub_gen = SubtitleGenerator()
        renderer = VideoRenderer()

        self.pipeline = KaraokePipeline(
            separator=None, # type: ignore
            transcriber=None, # type: ignore
            sub_gen=sub_gen,
            renderer=renderer,
            on_log=self.manual_log_panel.log
        )
        
        # Pipeline callbacks setup
        self.pipeline.on_step_start = self._step_start
        self.pipeline.on_step_progress = self._step_progress
        self.pipeline.on_step_done = self._step_done

        # Arkaplanda işle
        self._processing_thread = threading.Thread(
            target=self._run_manual_pipeline,
            args=(words, audio_path, output_path, ass_path, lrc_path),
            daemon=True
        )
        self._processing_thread.start()

    def _run_manual_pipeline(self, words: list, audio_path: str, output_path: str, ass_path: str, lrc_path: str):
        import traceback
        try:
            self.pipeline.run_from_words(words, audio_path, output_path, ass_path, lrc_path)
            if not self._is_processing:
                return
            self.after(0, lambda: self._on_complete(output_path, lrc_path))
        except Exception as e:
            err_msg = str(e)
            if "İşlem kullanıcı tarafından iptal edildi" in err_msg:
                self.after(0, lambda: self._set_status("İptal edildi"))
            else:
                tb = traceback.format_exc()
                self.after(0, lambda err=err_msg, t=tb: self._on_error(err, t))
        finally:
            if os.path.exists(ass_path):
                try:
                    os.remove(ass_path)
                except Exception:
                    pass

    def _cancel_processing(self):
        if self.pipeline:
            self.pipeline.cancel()
        self._is_processing = False
        active_tab = self.tabview.get()
        logp = self.log_panel if active_tab == "Otomatik Oluştur" else self.manual_log_panel
        logp.log("İşlem iptal ediliyor...", "warning")
        self._set_status("İptal edildi")
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")

    def _run_pipeline(self, mp3_path: str, output_dir: str):
        """Tüm işlem pipeline'ını çalıştırır (arkaplan thread'i)."""
        import traceback

        try:
            results = self.pipeline.run(mp3_path, output_dir)
            if not self._is_processing:
                return
            self.after(0, lambda: self._on_complete(results["video"], results["lrc"]))

        except Exception as e:
            err_msg = str(e)
            if "İşlem kullanıcı tarafından iptal edildi" in err_msg:
                self.after(0, lambda: self._set_status("İptal edildi"))
            else:
                tb = traceback.format_exc()
                self.after(0, lambda err=err_msg, t=tb: self._on_error(err, t))

    def _step_start(self, index: int, name: str = ""):
        self.after(0, lambda: self.step_progress.set_step_state(index, "running"))
        step_name = name if name else StepProgressBar.STEPS[index][1]
        self.after(0, lambda: self._set_status(
            f"Adım {index + 1}/4: {step_name}..."
        ))

    def _step_progress(self, index: int, value: float):
        self.after(0, lambda: self.step_progress.update_progress(index, value))

    def _step_done(self, index: int):
        self.after(0, lambda: self.step_progress.set_step_state(index, "done"))

    def _on_complete(self, output_path: str, lrc_path: str):
        self._is_processing = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self._set_status("✅ Karaoke videosu başarıyla oluşturuldu!")

        active_tab = self.tabview.get()
        logp = self.log_panel if active_tab == "Otomatik Oluştur" else self.manual_log_panel

        logp.log("═══════════════════════════════════", "success")
        logp.log("TÜM ADIMLAR TAMAMLANDI!", "success")
        logp.log(f"Video: {output_path}", "accent")
        logp.log(f"Şarkı Sözleri (.lrc): {lrc_path}", "accent")
        logp.log("═══════════════════════════════════", "success")

        # Tamamlandı penceresi
        result = messagebox.askyesno(
            "🎉 Tamamlandı!",
            f"Karaoke videosu başarıyla oluşturuldu!\n\n"
            f"📁 {output_path}\n\n"
            f"Videoyu şimdi açmak ister misiniz?",
            icon="info"
        )
        if result:
            os.startfile(output_path)

    def _on_error(self, error: str, traceback_str: str):
        self._is_processing = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")

        active_tab = self.tabview.get()
        prog = self.step_progress # Tab 1'deki ana ilerleme barını güncelliyoruz
        logp = self.log_panel if active_tab == "Otomatik Oluştur" else self.manual_log_panel

        for i in range(4):
            if prog.step_widgets[i]._icon_label.cget("text") not in ("✓", "✗"):
                prog.set_step_state(i, "error")
                break

        logp.log(f"HATA: {error}", "error")
        self._set_status(f"❌ Hata: {error[:60]}...")

        messagebox.showerror("Hata Oluştu", f"İşlem sırasında hata:\n\n{error}")

    def _open_lyrics_editor(self):
        # Open a new CTkToplevel window
        editor_win = ctk.CTkToplevel(self)
        editor_win.title("Şarkı Sözü Düzenleyici (Tam Ekran)")
        
        # Try to maximize the window (Windows zoomed state)
        try:
            editor_win.state("zoomed")
        except Exception:
            # Fallback to large geometry if zoomed state is not supported
            win_w = 1000
            win_h = 750
            screen_w = editor_win.winfo_screenwidth()
            screen_h = editor_win.winfo_screenheight()
            pos_x = (screen_w - win_w) // 2
            pos_y = (screen_h - win_h) // 2
            editor_win.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
            
        editor_win.configure(fg_color=COLORS["bg_primary"])
        
        # Make it modal & transient
        editor_win.transient(self)
        editor_win.grab_set()
        
        # Layout
        editor_win.grid_columnconfigure(0, weight=1)
        editor_win.grid_rowconfigure(1, weight=1) # Textbox gets all vertical space
        
        # Header
        header_frame = ctk.CTkFrame(editor_win, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=SIZES["padding_lg"], pady=(SIZES["padding_lg"], 8))
        header_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header_frame, 
            text="📝  Şarkı Sözleri Düzenleme Paneli", 
            font=ctk.CTkFont("Segoe UI", 20, "bold"), 
            text_color=COLORS["accent_glow"]
        ).grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(
            header_frame, 
            text="İmla ve kelime hatalarını buradan düzenleyebilirsiniz. Kelime sayısının orijinal sayı ile aynı kalması, kelime-zamanlama eşleştirmesinin 1:1 doğru olması için önerilir.", 
            font=ctk.CTkFont(*FONTS["body"]), 
            text_color=COLORS["text_secondary"]
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        
        # Textbox Frame (adds padding and background)
        tb_frame = ctk.CTkFrame(editor_win, fg_color=COLORS["bg_secondary"], corner_radius=SIZES["corner_radius"])
        tb_frame.grid(row=1, column=0, sticky="nsew", padx=SIZES["padding_lg"], pady=8)
        tb_frame.grid_columnconfigure(0, weight=1)
        tb_frame.grid_rowconfigure(0, weight=1)
        
        tb = ctk.CTkTextbox(
            tb_frame, 
            font=ctk.CTkFont("Consolas", 14), 
            fg_color=COLORS["bg_input"], 
            border_color=COLORS["border"], 
            border_width=1, 
            text_color=COLORS["text_primary"], 
            wrap="word"
        )
        tb.grid(row=0, column=0, sticky="nsew", padx=SIZES["padding_md"], pady=SIZES["padding_md"])
        
        # Insert current text
        tb.insert("1.0", self.lyrics_text)
        tb.focus_set()
        
        # Word count label inside editor window for real-time feedback
        count_lbl = ctk.CTkLabel(
            editor_win, 
            text="", 
            font=ctk.CTkFont("Segoe UI", 12, "bold")
        )
        count_lbl.grid(row=2, column=0, sticky="w", padx=SIZES["padding_lg"], pady=6)
        
        def update_editor_counts(event=None):
            orig_count = len(self.original_words)
            current_text = tb.get("1.0", "end").strip()
            edited_words = current_text.split()
            edited_count = len(edited_words)
            
            lbl_text = f"Kelime Sayısı — Orijinal: {orig_count} | Düzenlenen: {edited_count}"
            if orig_count == edited_count:
                color = COLORS["success"]
                lbl_text += " (Zamanlamalar 1:1 eşleşiyor ✓)"
            else:
                color = COLORS["warning"]
                lbl_text += " (Farklı kelime sayısı: Zamanlamalar orantılı dağıtılacaktır ⚠)"
            count_lbl.configure(text=lbl_text, text_color=color)
            
        tb.bind("<KeyRelease>", update_editor_counts)
        update_editor_counts() # initial run
        
        # Footer
        footer_frame = ctk.CTkFrame(editor_win, fg_color="transparent")
        footer_frame.grid(row=3, column=0, sticky="ew", padx=SIZES["padding_lg"], pady=SIZES["padding_lg"])
        footer_frame.grid_columnconfigure(0, weight=1)
        
        def save_and_close():
            self.lyrics_text = tb.get("1.0", "end").strip()
            self._update_word_counts()
            self._validate_inputs()
            editor_win.destroy()
            
        # Cancel Button
        cancel_btn = ctk.CTkButton(
            footer_frame, 
            text="Vazgeç", 
            width=120, 
            height=44,
            fg_color=COLORS["bg_tertiary"], 
            hover_color=COLORS["error"], 
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(*FONTS["body_bold"]),
            command=editor_win.destroy
        )
        cancel_btn.grid(row=0, column=1, padx=(0, 12))
        
        # Save Button
        save_btn = ctk.CTkButton(
            footer_frame, 
            text="💾  Değişiklikleri Uygula", 
            width=220, 
            height=44,
            fg_color=COLORS["accent_secondary"], 
            hover_color=COLORS["accent_primary"], 
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=save_and_close
        )
        save_btn.grid(row=0, column=2)
        
        # Force focus after a short delay
        editor_win.after(100, lambda: editor_win.focus_force())
