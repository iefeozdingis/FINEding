"""Global arama — Ctrl+F ile tüm işlem ve borçlarda anında arama."""

from tkinter import ttk

import customtkinter as ctk

from ui.utils import para_formatla, treeview_tema_uygula


class GlobalAramaPenceresi(ctk.CTkToplevel):
    """Kategori, açıklama, etiket, kişi veya tutara göre tüm uygulamada arar."""

    def __init__(self, parent, db, dashboard_ac, planlama_ac):
        super().__init__(parent)
        self.db = db
        self._dashboard_ac = dashboard_ac
        self._planlama_ac = planlama_ac
        self._sonuclar = []

        self.title("🔍 Ara")
        self.geometry("640x440")
        self.transient(parent.winfo_toplevel())
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(
            self, text="🔍 Tüm Uygulamada Ara", font=("Segoe UI", 18, "bold")
        ).pack(pady=(16, 8))

        self.arama = ctk.CTkEntry(
            self, width=560, height=40,
            placeholder_text="Kategori, açıklama, etiket, kişi veya tutar yazın...",
        )
        self.arama.pack(pady=8)
        self.arama.bind("<KeyRelease>", self._ara)
        self.arama.bind("<Escape>", lambda e: self.destroy())
        self.arama.bind("<Return>", self._sonuca_git)

        treeview_tema_uygula()
        kolonlar = ("Tip", "Tarih", "Kategori", "Açıklama", "Tutar")
        self.sonuc_liste = ttk.Treeview(
            self, columns=kolonlar, show="headings", height=13,
        )
        genislikler = {"Tip": 70, "Tarih": 90, "Kategori": 110, "Açıklama": 190, "Tutar": 100}
        for k in kolonlar:
            self.sonuc_liste.heading(k, text=k)
            self.sonuc_liste.column(k, width=genislikler[k], anchor="center")
        self.sonuc_liste.pack(fill="both", expand=True, padx=16, pady=8)
        self.sonuc_liste.bind("<Double-Button-1>", self._sonuca_git)

        ctk.CTkLabel(
            self, text="Çift tıkla veya Enter'a bas: ilgili sayfaya götürür",
            font=("Segoe UI", 11), text_color="#94a3b8",
        ).pack(pady=(0, 12))

        self.arama.focus_set()

    def _ara(self, event=None):
        metin = self.arama.get().strip()
        self.sonuc_liste.delete(*self.sonuc_liste.get_children())
        self._sonuclar = []
        if not metin:
            return

        for row in self.db.islem_ara(metin)[:30]:
            tarih, tur, kategori, aciklama, tutar = row[1], row[2], row[3], row[4], row[5]
            self.sonuc_liste.insert(
                "", "end",
                values=(tur, tarih, kategori, aciklama or "", para_formatla(tutar)),
            )
            self._sonuclar.append("islem")

        metin_kucuk = metin.lower()
        for b in self.db.borclari_listele("Tümü"):
            hedef = f"{b['aciklama']} {b.get('kisi') or ''} {b['tur']}".lower()
            if metin_kucuk in hedef:
                self.sonuc_liste.insert(
                    "", "end",
                    values=(
                        b["tur"], b.get("vade_tarih") or "", b.get("kisi") or "",
                        b["aciklama"], para_formatla(b['kalan_tutar']),
                    ),
                )
                self._sonuclar.append("borc")

    def _sonuca_git(self, event=None):
        secili = self.sonuc_liste.selection()
        if not secili:
            return
        idx = self.sonuc_liste.index(secili[0])
        tip = self._sonuclar[idx]
        self.destroy()
        if tip == "islem":
            self._dashboard_ac()
        else:
            self._planlama_ac()
