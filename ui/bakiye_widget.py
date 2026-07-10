"""Masaüstü bakiye widget'ı — her zaman üstte mini bakiye göstergesi."""

import threading
import time
from pathlib import Path

import customtkinter as ctk


class BakiyeWidget(ctk.CTk):
    """Masaüstünde sabit duran, frameless mini bakiye penceresi."""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("💎 FINEding — Bakiye")
        self.geometry("200x50")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.configure(fg_color="#0f172a")
        self.overrideredirect(True)

        # Sağ alt köşe
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{sw - 210}+{sh - 80}")

        # Sürükleme
        self._offset_x = 0
        self._offset_y = 0
        self.bind("<Button-1>", self._tiklama_basla)
        self.bind("<B1-Motion>", self._surukle)
        self.bind("<Button-3>", lambda e: self.kapat())

        self._label = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 14, "bold"),
            text_color="#ffffff",
        )
        self._label.pack(expand=True, fill="both", padx=8, pady=4)

        self.guncelle()
        self._durdur = False
        t = threading.Thread(target=self._periyodik_guncelle, daemon=True)
        t.start()

        self.protocol("WM_DELETE_WINDOW", self.kapat)

    def _tiklama_basla(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _surukle(self, event):
        x = self.winfo_x() + event.x - self._offset_x
        y = self.winfo_y() + event.y - self._offset_y
        self.geometry(f"+{x}+{y}")

    def _sag_tik(self, event):
        menu = ctk.CTkToplevel(self)
        menu.title("")
        menu.geometry("160x120")
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        menu.configure(fg_color="#1e293b")
        menu.geometry(f"+{event.x_root}+{event.y_root}")

        ctk.CTkButton(
            menu, text="🔄 Güncelle", width=140, height=30,
            fg_color="transparent", hover_color="#334155",
            command=lambda: [self.guncelle(), menu.destroy()],
        ).pack(pady=(5, 0))

        ctk.CTkButton(
            menu, text="📊 Dashboard Aç", width=140, height=30,
            fg_color="transparent", hover_color="#334155",
            command=lambda: [self._dashboard_ac(), menu.destroy()],
        ).pack()

        ctk.CTkButton(
            menu, text="❌ Kapat", width=140, height=30,
            fg_color="transparent", hover_color="#dc2626",
            text_color="#ef4444",
            command=lambda: [self.kapat(), menu.destroy()],
        ).pack()

        menu.focus_force()
        menu.bind("<FocusOut>", lambda e: menu.destroy())

    def _dashboard_ac(self):
        """Ana uygulamayı aç veya öne getir."""
        try:
            import subprocess
            subprocess.Popen(
                [str(Path(__file__).parent.parent / ".venv" / "Scripts" / "pythonw.exe"),
                 str(Path(__file__).parent.parent / "main.py")],
            )
        except Exception:
            pass

    def guncelle(self):
        try:
            bakiye = self.db.bakiye()
            renk = "#22c55e" if bakiye >= 0 else "#ef4444"
            emoji = "📈" if bakiye >= 0 else "📉"
            self._label.configure(
                text=f"{emoji} Bakiye: {bakiye:,.2f} ₺",
                text_color=renk,
            )
        except Exception:
            self._label.configure(text="💰 --- ₺", text_color="#64748b")

    def _periyodik_guncelle(self):
        while not self._durdur:
            time.sleep(30)
            try:
                self.after(0, self.guncelle)
            except Exception:
                break

    def kapat(self):
        self._durdur = True
        self.destroy()

    @staticmethod
    def baslat(db):
        """Widget'ı bağımsız bir thread'de başlat."""
        def _run():
            widget = BakiyeWidget(db)
            widget.mainloop()
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t
