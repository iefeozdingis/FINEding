"""Masaüstü bakiye widget'ı — her zaman üstte mini bakiye göstergesi."""

import customtkinter as ctk

from ui.money import para_formatla


class BakiyeWidget(ctk.CTkToplevel):
    """Masaüstünde sabit duran, frameless mini bakiye penceresi.

    Ana pencerenin mainloop'unu paylaşması için CTkToplevel kullanılır —
    bağımsız bir CTk() penceresi kendi olay döngüsü hiç işletilmediği
    için hiçbir zaman ekrana çizilmiyordu (görünmez kalıyordu).
    """

    def __init__(self, master, db, ana_pencere_callback=None):
        super().__init__(master)
        self.db = db
        self._ana_pencere_callback = ana_pencere_callback
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
        self.bind("<Button-3>", self._sag_tik)

        self._label = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 14, "bold"),
            text_color="#ffffff",
        )
        self._label.pack(expand=True, fill="both", padx=8, pady=4)

        self.guncelle()
        # Tk thread-safe olmadığı için periyodik güncelleme ayrı thread'den
        # after(0, ...) çağırmak yerine doğrudan Tk'nin after zamanlamasıyla
        # ana thread üzerinde yapılır (nadir crash ve sızıntı riski ortadan kalkar).
        self._after_id = self.after(30000, self._periyodik_guncelle)

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
        """Ana uygulamayı öne getirir (aynı process içinde zaten çalışıyor)."""
        if self._ana_pencere_callback:
            try:
                self._ana_pencere_callback()
            except Exception:
                pass

    def guncelle(self):
        try:
            bakiye = self.db.bakiye()
            renk = "#22c55e" if bakiye >= 0 else "#ef4444"
            emoji = "📈" if bakiye >= 0 else "📉"
            self._label.configure(
                text=f"{emoji} Bakiye: {para_formatla(bakiye)}",
                text_color=renk,
            )
        except Exception:
            self._label.configure(text="💰 --- ₺", text_color="#64748b")

    def _periyodik_guncelle(self):
        """Kendini yeniden zamanlayan periyodik güncelleme (ana thread)."""
        self.guncelle()
        self._after_id = self.after(30000, self._periyodik_guncelle)

    def kapat(self):
        if getattr(self, "_after_id", None) is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self.destroy()
