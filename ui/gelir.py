import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime


class GelirSayfasi(ctk.CTkFrame):

    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent)

        self.db = db
        self.dashboard_callback = dashboard_callback

        self.grid_columnconfigure(0, weight=1)

        # Başlık
        baslik = ctk.CTkLabel(
            self,
            text="💰 Gelir Ekle",
            font=("Segoe UI", 28, "bold")
        )
        baslik.pack(pady=20)

        # Tarih
        self.tarih = ctk.CTkEntry(
            self,
            width=350,
            placeholder_text="Tarih (GG.AA.YYYY)"
        )
        self.tarih.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.tarih.pack(pady=10)

        # Kategori
        self.kategori = ctk.CTkComboBox(
            self,
            width=350,
            values=[
                "Maaş",
                "Prim",
                "Ek İş",
                "Faiz",
                "Yatırım",
                "Diğer"
            ]
        )
        self.kategori.set("Maaş")
        self.kategori.pack(pady=10)

        # Açıklama
        self.aciklama = ctk.CTkEntry(
            self,
            width=350,
            placeholder_text="Açıklama"
        )
        self.aciklama.pack(pady=10)

        # Tutar
        self.tutar = ctk.CTkEntry(
            self,
            width=350,
            placeholder_text="Tutar"
        )
        self.tutar.pack(pady=10)

        # Kaydet Butonu
        self.kaydet_btn = ctk.CTkButton(
            self,
            text="💾 Geliri Kaydet",
            width=200,
            height=40,
            command=self.kaydet
        )
        self.kaydet_btn.pack(pady=25)

    def kaydet(self):

        try:

            tutar = float(self.tutar.get())

            self.db.gelir_ekle(
                self.tarih.get(),
                self.kategori.get(),
                self.aciklama.get(),
                tutar
            )

            messagebox.showinfo(
                "Başarılı",
                "Gelir başarıyla kaydedildi."
            )

            self.aciklama.delete(0, "end")
            self.tutar.delete(0, "end")

            if self.dashboard_callback:
                self.dashboard_callback()

        except ValueError:

            messagebox.showerror(
                "Hata",
                "Lütfen geçerli bir tutar giriniz."
            )

        except Exception as e:

            messagebox.showerror(
                "Hata",
                str(e)
            )