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
        main = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg_primary"],
                                       scrollbar_button_color=COLORS["bg_tertiary"])
        main.grid(row=1, column=0, sticky="nsew")
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

        # ── 5. İlerleme ve Log ──
        bottom_frame = ctk.CTkFrame(main, fg_color="transparent")
        bottom_frame.grid(row=row, column=0, sticky="ew",
                           padx=SIZES["padding_lg"],
                           pady=(0, SIZES["padding_xl"]))
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=1)
        row += 1

        self.step_progress = StepProgressBar(bottom_frame)
        self.step_progress.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.log_panel = LogPanel(bottom_frame, height=280)
        self.log_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # GPU ipucunu güncelle (asenkron)
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

    def _validate_inputs(self):
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

    def _set_status(self, text: str):
        self.status_label.configure(text=text)

    # ─── İşlem Yönetimi ──────────────────────────────────────────────────────

    def _start_processing(self):
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

    def _cancel_processing(self):
        if self.pipeline:
            self.pipeline.cancel()
        self._is_processing = False
        self.log_panel.log("İşlem iptal ediliyor...", "warning")
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

    def _step_start(self, index: int):
        self.after(0, lambda: self.step_progress.set_step_state(index, "running"))
        self.after(0, lambda: self._set_status(
            f"Adım {index + 1}/4: {StepProgressBar.STEPS[index][1]}..."
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

        self.log_panel.log("═══════════════════════════════════", "success")
        self.log_panel.log("TÜM ADIMLAR TAMAMLANDI!", "success")
        self.log_panel.log(f"Video: {output_path}", "accent")
        self.log_panel.log(f"Şarkı Sözleri (.lrc): {lrc_path}", "accent")
        self.log_panel.log("═══════════════════════════════════", "success")

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

        for i in range(4):
            if self.step_progress.step_widgets[i]._icon_label.cget("text") not in ("✓", "✗"):
                self.step_progress.set_step_state(i, "error")
                break

        self.log_panel.log(f"HATA: {error}", "error")
        self._set_status(f"❌ Hata: {error[:60]}...")

        messagebox.showerror("Hata Oluştu", f"İşlem sırasında hata:\n\n{error}")
