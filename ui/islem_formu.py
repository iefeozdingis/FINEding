"""Gelir/Gider ekleme için ortak form sayfası.

gelir.py ve gider.py neredeyse birebir kopyaydı (yalnızca renk, başlık,
varsayılan kategori ve çağrılan db metodu farklıydı). Tek parametrik sınıfta
birleştirildi; gelir.py/gider.py ince sarmalayıcılara indirildi.
"""

from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from ui import tema
from ui.utils import kategori_listesi, tarih_bind, tutar_bind, tutar_oku


class IslemFormuSayfasi(ctk.CTkFrame):
    def __init__(
        self, parent, db, tur, kategoriler, varsayilan_kategori,
        renk, kart_renk, dashboard_callback=None,
    ):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.tur = tur  # "Gelir" | "Gider"
        self.varsayilan_kategoriler = kategoriler
        self.renk = renk
        self.dashboard_callback = dashboard_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        kart = ctk.CTkFrame(
            self, corner_radius=20, fg_color=kart_renk,
            border_width=1, border_color=renk,
        )
        kart.pack(pady=30, padx=40, fill="both", expand=True)

        ikon = "💰" if tur == "Gelir" else "💸"
        baslik_renk = ("#15803d", "#4ade80") if tur == "Gelir" else ("#b91c1c", "#f87171")
        ctk.CTkLabel(
            kart, text=f"{ikon}  {tur} Ekle",
            font=("Segoe UI", 30, "bold"), text_color=baslik_renk,
        ).pack(pady=(30, 10))
        ctk.CTkLabel(
            kart, text=f"Yeni bir {tur.lower()} kaydı oluştur",
            font=("Segoe UI", 13), text_color=tema.METIN_SOLUK,
        ).pack(pady=(0, 25))

        form = ctk.CTkFrame(kart, fg_color="transparent")
        form.pack(pady=10)

        self.tarih = ctk.CTkEntry(
            form, width=380, height=42, placeholder_text="Tarih (GG.AA.YYYY)",
            font=("Segoe UI", 14), corner_radius=10, border_color=renk,
        )
        self.tarih.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.tarih.pack(pady=8)
        tarih_bind(self.tarih)

        self.kategori = ctk.CTkComboBox(
            form, width=380, height=42, values=self._kategori_listesi(),
            font=("Segoe UI", 14), corner_radius=10, border_color=renk,
            button_color=renk,
        )
        self.kategori.set(varsayilan_kategori)
        self.kategori.pack(pady=8)

        self.aciklama = ctk.CTkEntry(
            form, width=380, height=42, placeholder_text="Açıklama",
            font=("Segoe UI", 14), corner_radius=10, border_color=renk,
        )
        self.aciklama.pack(pady=8)

        self.tutar = ctk.CTkEntry(
            form, width=380, height=42, placeholder_text="Tutar (₺)",
            font=("Segoe UI", 14), corner_radius=10, border_color=renk,
        )
        self.tutar.pack(pady=8)
        tutar_bind(self.tutar)

        self.etiketler = ctk.CTkEntry(
            form, width=380, height=42,
            placeholder_text="Etiketler (virgülle ayır, örn: iş, önemli)",
            font=("Segoe UI", 14), corner_radius=10, border_color=renk,
        )
        self.etiketler.pack(pady=8)

        self.kaydet_btn = ctk.CTkButton(
            kart, text=f"💾  {tur}i Kaydet", width=280, height=45,
            font=("Segoe UI", 15, "bold"), fg_color=renk,
            corner_radius=12, command=self.kaydet,
        )
        self.kaydet_btn.pack(pady=(25, 30))

        # Enter ile kaydet (tutar/etiket alanından) — hızlı işlem popup'ıyla
        # ve giriş ekranıyla tutarlı
        for w in (self.tutar, self.etiketler, self.aciklama):
            w.bind("<Return>", lambda e: self.kaydet())

    def _kategori_listesi(self) -> list:
        # Birleştirme mantığı ui.utils.kategori_listesi'nde tek yerde
        return kategori_listesi(self.db, self.tur)

    def kaydet(self):
        try:
            tutar = tutar_oku(self.tutar)
        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli bir tutar giriniz.")
            return

        if tutar <= 0:
            messagebox.showerror("Hata", "Tutar sıfırdan büyük olmalıdır.")
            return

        kategori = self.kategori.get().strip()
        if not kategori:
            messagebox.showerror("Hata", "Lütfen bir kategori giriniz.")
            return

        # Tarihi kaydetmeden önce doğrula (yanlış tarihi 'geçersiz tutar'
        # diye raporlamamak için)
        from database import normalize_date
        try:
            normalize_date(self.tarih.get())
        except ValueError:
            messagebox.showerror(
                "Hata",
                f"'{self.tarih.get()}' geçerli bir tarih değil. "
                "GG.AA.YYYY biçiminde girin (örn: 15.07.2026).",
            )
            return

        try:
            self.db.kategori_ekle(self.tur, kategori)
            self.kategori.configure(values=self._kategori_listesi())
            ekle = self.db.gelir_ekle if self.tur == "Gelir" else self.db.gider_ekle
            ekle(
                self.tarih.get(), kategori, self.aciklama.get(), tutar,
                self.etiketler.get().strip(),
            )
        except Exception as e:
            messagebox.showerror("Hata", str(e))
            return

        messagebox.showinfo("Başarılı", f"{self.tur} başarıyla kaydedildi.")
        self.aciklama.delete(0, "end")
        self.tutar.delete(0, "end")
        self.etiketler.delete(0, "end")
        if self.dashboard_callback:
            self.dashboard_callback()
