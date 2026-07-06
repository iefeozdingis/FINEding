from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox


class ButceSayfasi(ctk.CTkFrame):

    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent)
        self.db = db
        self.dashboard_callback = dashboard_callback
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="📅 Bütçe Yönetimi", font=("Segoe UI", 28, "bold")).pack(pady=20)

        simdi = datetime.now()
        self.ay = ctk.CTkEntry(self, width=220, placeholder_text="Ay")
        self.ay.insert(0, str(simdi.month))
        self.ay.pack(pady=6)

        self.yil = ctk.CTkEntry(self, width=220, placeholder_text="Yıl")
        self.yil.insert(0, str(simdi.year))
        self.yil.pack(pady=6)

        self.kategori = ctk.CTkEntry(self, width=220, placeholder_text="Kategori")
        self.kategori.pack(pady=6)

        self.tutar = ctk.CTkEntry(self, width=220, placeholder_text="Bütçe Tutarı")
        self.tutar.pack(pady=6)

        ctk.CTkButton(self, text="💾 Bütçeyi Kaydet", width=220, command=self.kaydet).pack(pady=16)

        self.listbox = ctk.CTkTextbox(self, height=260)
        self.listbox.pack(fill="both", expand=True, padx=20, pady=10)
        self.goster()

    def kaydet(self):
        try:
            self.db.kaydet_butce(int(self.ay.get()), int(self.yil.get()), self.kategori.get(), float(self.tutar.get()))
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
            for item in self.db.butce_durumu(ay, yil):
                self.listbox.insert(
                    "end",
                    f"{item['kategori']}: Bütçe {item['butce']:,.2f} ₺ | Harcanan {item['harcanan']:,.2f} ₺ | Kalan {item['kalan']:,.2f} ₺\n"
                )
        else:
            self.listbox.insert("end", "Geçerli bir ay ve yıl girin.")
