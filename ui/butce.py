from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from ui.utils import para_formatla, tutar_bind, tutar_oku


class ButceSayfasi(ctk.CTkFrame):
    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent)
        self.db = db
        self.dashboard_callback = dashboard_callback
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="📅 Bütçe Yönetimi", font=("Segoe UI", 28, "bold")
        ).pack(pady=20)

        simdi = datetime.now()
        self.ay = ctk.CTkEntry(self, width=220, placeholder_text="Ay (1-12)")
        self.ay.insert(0, str(simdi.month))
        self.ay.pack(pady=6)

        self.yil = ctk.CTkEntry(self, width=220, placeholder_text="Yıl (örn: 2026)")
        self.yil.insert(0, str(simdi.year))
        self.yil.pack(pady=6)

        self.kategori = ctk.CTkComboBox(
            self,
            width=220,
            values=self._kategori_listesi(),
        )
        self.kategori.set("Market")
        self.kategori.pack(pady=6)

        self.tutar = ctk.CTkEntry(self, width=220, placeholder_text="Bütçe Tutarı")
        self.tutar.pack(pady=6)
        tutar_bind(self.tutar)

        ctk.CTkButton(
            self, text="💾 Bütçeyi Kaydet", width=220, command=self.kaydet
        ).pack(pady=16)

        self.listbox = ctk.CTkTextbox(self, height=260)
        self.listbox.pack(fill="both", expand=True, padx=20, pady=10)
        self.goster()

    def _kategori_listesi(self) -> list:
        varsayilan = [
            "Maaş",
            "Prim",
            "Ek İş",
            "Faiz",
            "Yatırım",
            "Market",
            "Kira",
            "Fatura",
            "Yakıt",
            "Yemek",
            "Sağlık",
            "Eğlence",
            "Diğer",
        ]
        ozel_gelir = self.db.kategorileri_getir("Gelir")
        ozel_gider = self.db.kategorileri_getir("Gider")
        tumu = varsayilan + ozel_gelir + ozel_gider
        return list(dict.fromkeys(tumu))  # sırayı koruyarak tekrarları kaldır

    def kaydet(self):
        try:
            ay = int(self.ay.get() or 0)
            yil = int(self.yil.get() or 0)
            if ay < 1 or ay > 12:
                messagebox.showerror("Hata", "Ay 1-12 arasında olmalıdır.")
                return
            if yil < 2000 or yil > 2100:
                messagebox.showerror("Hata", "Geçerli bir yıl giriniz (2000-2100).")
                return
            tutar = tutar_oku(self.tutar)
            if tutar <= 0:
                messagebox.showerror("Hata", "Bütçe tutarı sıfırdan büyük olmalıdır.")
                return
            self.db.kaydet_butce(ay, yil, self.kategori.get(), tutar)
            messagebox.showinfo("Başarılı", "Bütçe kaydedildi.")
            self.goster()
            if self.dashboard_callback:
                self.dashboard_callback()
        except Exception as hata:
            messagebox.showerror("Hata", str(hata))

    def goster(self):
        self.listbox.delete("1.0", "end")
        ay = int(self.ay.get() or 0)
        yil = int(self.yil.get() or 0)
        if ay and yil:
            durumlar = self.db.butce_durumu(ay, yil)
            if not durumlar:
                self.listbox.insert("end", "Bu ay için henüz bütçe tanımlanmamış.\n")
                return

            asim_var = False
            for item in durumlar:
                kategori = item["kategori"]
                butce_str = para_formatla(item['butce'])
                harcanan_str = para_formatla(item['harcanan'])
                kalan_str = para_formatla(item['kalan'])
                durum_icon = "✅"
                if item["kalan"] < 0:
                    durum_icon = "🔴 AŞILDI!"
                    asim_var = True
                elif item["kalan"] < item["butce"] * 0.1:
                    durum_icon = "🟡 Yaklaşıyor"
                line = (
                    f"{durum_icon} {kategori}: Bütçe {butce_str}"
                    f" | Harcanan {harcanan_str} | Kalan {kalan_str}\n"
                )
                self.listbox.insert("end", line)

            if asim_var:
                self.listbox.insert(
                    "end", "\n⚠️ UYARI: Bazı kategorilerde bütçe aşıldı!\n"
                )
        else:
            self.listbox.insert("end", "Geçerli bir ay ve yıl girin.")
