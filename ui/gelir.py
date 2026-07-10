from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from ui.utils import tarih_bind, tutar_bind, tutar_oku

# Varsayılan gelir kategorileri
VARSAYILAN_GELIR_KATEGORILER = ["Maaş", "Prim", "Ek İş", "Faiz", "Yatırım", "Diğer"]


class GelirSayfasi(ctk.CTkFrame):
    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent, fg_color="transparent")

        self.db = db
        self.dashboard_callback = dashboard_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Ana kart
        kart = ctk.CTkFrame(
            self,
            corner_radius=20,
            fg_color="#0d2818",
            border_width=1,
            border_color="#2e8b57",
        )
        kart.pack(pady=30, padx=40, fill="both", expand=True)

        # Başlık
        ctk.CTkLabel(
            kart,
            text="💰  Gelir Ekle",
            font=("Segoe UI", 30, "bold"),
            text_color="#4ade80",
        ).pack(pady=(30, 10))

        ctk.CTkLabel(
            kart,
            text="Yeni bir gelir kaydı oluştur",
            font=("Segoe UI", 13),
            text_color="#94a3b8",
        ).pack(pady=(0, 25))

        # Form alanları
        form = ctk.CTkFrame(kart, fg_color="transparent")
        form.pack(pady=10)

        self.tarih = ctk.CTkEntry(
            form,
            width=380,
            height=42,
            placeholder_text="Tarih (GG.AA.YYYY)",
            font=("Segoe UI", 14),
            corner_radius=10,
            border_color="#2e8b57",
        )
        self.tarih.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.tarih.pack(pady=8)
        tarih_bind(self.tarih)

        self.kategori = ctk.CTkComboBox(
            form,
            width=380,
            height=42,
            values=self._kategori_listesi(),
            font=("Segoe UI", 14),
            corner_radius=10,
            border_color="#2e8b57",
            button_color="#2e8b57",
            button_hover_color="#1a4730",
        )
        self.kategori.set("Maaş")
        self.kategori.pack(pady=8)

        self.aciklama = ctk.CTkEntry(
            form,
            width=380,
            height=42,
            placeholder_text="Açıklama",
            font=("Segoe UI", 14),
            corner_radius=10,
            border_color="#2e8b57",
        )
        self.aciklama.pack(pady=8)

        self.tutar = ctk.CTkEntry(
            form,
            width=380,
            height=42,
            placeholder_text="Tutar (₺)",
            font=("Segoe UI", 14),
            corner_radius=10,
            border_color="#2e8b57",
        )
        self.tutar.pack(pady=8)
        tutar_bind(self.tutar)

        self.etiketler = ctk.CTkEntry(
            form,
            width=380,
            height=42,
            placeholder_text="Etiketler (virgülle ayır, örn: iş, önemli)",
            font=("Segoe UI", 14),
            corner_radius=10,
            border_color="#2e8b57",
        )
        self.etiketler.pack(pady=8)

        self.kaydet_btn = ctk.CTkButton(
            kart,
            text="💾  Geliri Kaydet",
            width=280,
            height=45,
            font=("Segoe UI", 15, "bold"),
            fg_color="#2e8b57",
            hover_color="#1a4730",
            corner_radius=12,
            command=self.kaydet,
        )
        self.kaydet_btn.pack(pady=(25, 30))

    def _kategori_listesi(self) -> list:
        ozel = self.db.kategorileri_getir("Gelir")
        return VARSAYILAN_GELIR_KATEGORILER + [
            k for k in ozel if k not in VARSAYILAN_GELIR_KATEGORILER
        ]

    def kaydet(self):
        try:
            tutar = tutar_oku(self.tutar)
            if tutar <= 0:
                messagebox.showerror("Hata", "Tutar sıfırdan büyük olmalıdır.")
                return

            kategori = self.kategori.get().strip()
            if not kategori:
                messagebox.showerror("Hata", "Lütfen bir kategori giriniz.")
                return

            # Yeni kategori ise kaydet ve listeyi güncelle
            self.db.kategori_ekle("Gelir", kategori)
            self.kategori.configure(values=self._kategori_listesi())

            self.db.gelir_ekle(
                self.tarih.get(), kategori, self.aciklama.get(), tutar,
                self.etiketler.get().strip(),
            )

            messagebox.showinfo("Başarılı", "Gelir başarıyla kaydedildi.")

            self.aciklama.delete(0, "end")
            self.tutar.delete(0, "end")
            self.etiketler.delete(0, "end")

            if self.dashboard_callback:
                self.dashboard_callback()

        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli bir tutar giriniz.")

        except Exception as e:
            messagebox.showerror("Hata", str(e))
