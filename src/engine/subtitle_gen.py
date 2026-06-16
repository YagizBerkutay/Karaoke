"""
subtitle_gen.py — .ass Karaoke Altyazı ve .lrc Üreteci
Kelime bazlı zaman damgalarından karaoke animasyonlu .ass dosyası
ve evrensel .lrc format dosyası üretir.
"""

import os
from typing import Callable, List, Dict, Any, Optional


# ─── ASS Karaoke Altyazı Üreteci ─────────────────────────────────────────────

class SubtitleGenerator:
    """
    .ass (Advanced SubStation Alpha) karaoke altyazı üreteci.
    
    \kf tag kullanımı:
        \\kf<centiseconds>  → kelimeyi soldan sağa renkle doldurur
        Bu tam olarak karaoke highlight animasyonu sağlar.
    """

    # Video boyutu
    WIDTH  = 1920
    HEIGHT = 1080

    # Tipografi ayarları
    FONT_NAME     = "Montserrat"   # FFmpeg içinde sistem fontuna düşer
    FONT_SIZE     = 68
    OUTLINE_SIZE  = 3
    SHADOW_SIZE   = 2

    # Renkler (ASS BGR hex formatı — RGB'nin tersi)
    COLOR_TEXT        = "&H00DDDDFF"  # Bekleyen kelime — açık gri-beyaz
    COLOR_HIGHLIGHT   = "&H00F050E0"  # Aktif kelime — lila/pembe
    COLOR_OUTLINE     = "&H00000000"  # Dış çizgi — siyah
    COLOR_SHADOW      = "&H80000000"  # Gölge — yarı saydam siyah

    # Kaç kelime satır başına
    WORDS_PER_LINE = 8

    def __init__(self, on_log: Optional[Callable[[str, str], None]] = None):
        self.on_log = on_log or (lambda m, l="info": None)

    def generate(self, words: List[Dict[str, Any]], output_path: str) -> str:
        """
        Kelime listesinden .ass karaoke dosyası üretir.
        
        Args:
            words: [{"word": str, "start": float, "end": float}, ...]
            output_path: Çıktı .ass dosya yolu
            
        Returns:
            Oluşturulan dosya yolu
        """
        self.on_log("ASS altyazı dosyası oluşturuluyor...", "info")

        lines = self._group_into_lines(words)
        self.on_log(f"{len(lines)} altyazı satırı oluşturuldu.", "info")

        ass_content = self._build_ass(lines, words)

        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(ass_content)

        size_kb = os.path.getsize(output_path) / 1024
        self.on_log(f"ASS dosyası kaydedildi: {size_kb:.1f} KB", "success")
        return output_path

    def generate_lrc(self, words: List[Dict[str, Any]], output_path: str) -> str:
        """
        Kelime listesinden .lrc (LRC) dosyası üretir.
        
        .lrc formatı: [mm:ss.xx]metin
        """
        self.on_log("LRC dosyası oluşturuluyor...", "info")
        lines = self._group_into_lines(words)

        lrc_lines = ["[ar:Karaoke Maker]", "[by:KaraokeMaker v1.0]", ""]

        for line_words in lines:
            if not line_words:
                continue
            start = line_words[0]["start"]
            mm = int(start // 60)
            ss = start % 60
            text = " ".join(w["word"] for w in line_words)
            lrc_lines.append(f"[{mm:02d}:{ss:05.2f}]{text}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lrc_lines))

        self.on_log(f"LRC dosyası kaydedildi: {output_path}", "success")
        return output_path

    # ─── Yardımcı Metodlar ────────────────────────────────────────────────────

    def _group_into_lines(
        self, words: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Kelimeleri satırlara böler.
        Satır sonu kriterleri:
          - WORDS_PER_LINE kelime dolusu
          - Kelimeler arası 2 saniyeden fazla sessizlik
          - Cümle sonu noktalama (.!?)
        """
        lines = []
        current_line = []

        for i, word in enumerate(words):
            # Sessizlik kontrolü
            if current_line and i > 0:
                gap = word["start"] - words[i - 1]["end"]
                if gap > 2.0:
                    if current_line:
                        lines.append(current_line)
                        current_line = []

            current_line.append(word)

            # Satır uzunluğu veya cümle sonu
            is_sentence_end = word["word"].rstrip().endswith((".", "!", "?", "،", "。"))
            if len(current_line) >= self.WORDS_PER_LINE or is_sentence_end:
                lines.append(current_line)
                current_line = []

        if current_line:
            lines.append(current_line)

        return lines

    def _build_ass(
        self,
        lines: List[List[Dict[str, Any]]],
        all_words: List[Dict[str, Any]],
    ) -> str:
        """Tam .ass dosya içeriğini oluşturur."""

        # Script başlığı
        header = self._ass_header()

        # Dialogue satırları
        dialogue_lines = []
        for line_words in lines:
            if not line_words:
                continue

            line_start = line_words[0]["start"]
            line_end   = line_words[-1]["end"]

            # Karaoke \kf tag'li metin oluştur
            karaoke_text = self._build_karaoke_text(line_words)

            # ASS zaman formatı: H:MM:SS.cs
            start_str = self._to_ass_time(line_start)
            end_str   = self._to_ass_time(line_end + 0.5)  # 0.5s ekstra görüntü

            dialogue = (
                f"Dialogue: 0,{start_str},{end_str},Karaoke,,0,0,0,,"
                f"{karaoke_text}"
            )
            dialogue_lines.append(dialogue)

        return header + "\n".join(dialogue_lines) + "\n"

    def _build_karaoke_text(self, line_words: List[Dict[str, Any]]) -> str:
        """
        \kf tag'lı karaoke metni oluşturur.
        \kf<n> → n centisaniye içinde kelimeyi doldur (sweep animasyonu)
        """
        parts = []
        for i, word in enumerate(line_words):
            duration_cs = int((word["end"] - word["start"]) * 100)
            duration_cs = max(duration_cs, 10)  # Minimum 10 cs

            text = word["word"]
            # Kelimeleri boşlukla ayır (son kelime hariç)
            if i < len(line_words) - 1:
                text = text + " "

            parts.append(f"{{\\kf{duration_cs}}}{text}")

        return "".join(parts)

    @staticmethod
    def _to_ass_time(seconds: float) -> str:
        """Saniyeyi ASS zaman formatına çevirir: H:MM:SS.cc"""
        seconds = max(0.0, seconds)
        h  = int(seconds // 3600)
        m  = int((seconds % 3600) // 60)
        s  = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def _ass_header(self) -> str:
        """ASS dosyası başlık bölümü."""
        return f"""[Script Info]
Title: Karaoke — KaraokeMaker v1.0
ScriptType: v4.00+
PlayResX: {self.WIDTH}
PlayResY: {self.HEIGHT}
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
Collisions: Normal

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{self.FONT_NAME},{self.FONT_SIZE},{self.COLOR_TEXT},{self.COLOR_HIGHLIGHT},{self.COLOR_OUTLINE},{self.COLOR_SHADOW},-1,0,0,0,100,100,2,0,1,{self.OUTLINE_SIZE},{self.SHADOW_SIZE},2,80,80,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
