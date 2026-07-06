import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime


class GiderSayfasi(ctk.CTkFrame):

    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent)

        self.db = db
        self.dashboard_callback = dashboard_callback

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="💸 Gider Ekle",
            font=("Segoe UI", 28, "bold")
        ).pack(pady=20)

        self.tarih = ctk.CTkEntry(
            self,
            width=350,
            placeholder_text="Tarih"
        )
        self.tarih.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.tarih.pack(pady=10)

        self.kategori = ctk.CTkComboBox(
            self,
            width=350,
            values=[
                "Market",
                "Kira",
                "Fatura",
                "Yakıt",
                "Yemek",
                "Sağlık",
                "Eğlence",
                "Diğer"
            ]
        )
        self.kategori.set("Market")
        self.kategori.pack(pady=10)

        self.aciklama = ctk.CTkEntry(
            self,
            width=350,
            placeholder_text="Açıklama"
        )
        self.aciklama.pack(pady=10)

        self.tutar = ctk.CTkEntry(
            self,
            width=350,
            placeholder_text="Tutar"
        )
        self.tutar.pack(pady=10)

        ctk.CTkButton(
            self,
            text="💾 Gideri Kaydet",
            width=220,
            height=40,
            command=self.kaydet
        ).pack(pady=20)

    def kaydet(self):

        try:

            self.db.gider_ekle(
                self.tarih.get(),
                self.kategori.get(),
                self.aciklama.get(),
                float(self.tutar.get())
            )

            messagebox.showinfo(
                "Başarılı",
                "Gider başarıyla kaydedildi."
            )

            self.aciklama.delete(0, "end")
            self.tutar.delete(0, "end")

            if self.dashboard_callback:
                self.dashboard_callback()

        except ValueError:

            messagebox.showerror(
                "Hata",
                "Geçerli bir tutar giriniz."
            )

        except Exception as e:

            messagebox.showerror(
                "Hata",
                str(e)
            )