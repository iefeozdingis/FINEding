import csv
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
from openpyxl import Workbook


class RaporlarSayfasi(ctk.CTkFrame):

    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent)
        self.db = db
        self.dashboard_callback = dashboard_callback
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="📄 Raporlar", font=("Segoe UI", 28, "bold")).pack(pady=20)

        simdi = datetime.now()
        ctk.CTkLabel(self, text="Başlangıç Tarihi", font=("Segoe UI", 14)).pack()
        self.baslangic = ctk.CTkEntry(self, width=300, placeholder_text="GG.AA.YYYY")
        self.baslangic.insert(0, simdi.strftime("%d.%m.%Y"))
        self.baslangic.pack(pady=6)

        ctk.CTkLabel(self, text="Bitiş Tarihi", font=("Segoe UI", 14)).pack()
        self.bitis = ctk.CTkEntry(self, width=300, placeholder_text="GG.AA.YYYY")
        self.bitis.insert(0, simdi.strftime("%d.%m.%Y"))
        self.bitis.pack(pady=6)

        ctk.CTkButton(self, text="📊 Raporu Göster", width=220, command=self.goster).pack(pady=16)
        ctk.CTkButton(self, text="⬇️ CSV Olarak Dışa Aktar", width=240, command=self.disa_aktar).pack(pady=8)
        ctk.CTkButton(self, text="📗 Excel Olarak Dışa Aktar", width=240, command=self.excel_aktar).pack(pady=8)

        self.ozet = ctk.CTkTextbox(self, height=220)
        self.ozet.pack(fill="both", expand=True, padx=20, pady=10)

    def goster(self):
        try:
            gelir = self.db.toplam_gelir_aralik(self.baslangic.get(), self.bitis.get())
            gider = self.db.toplam_gider_aralik(self.baslangic.get(), self.bitis.get())
            bakiye = gelir - gider
            self.ozet.delete("1.0", tk.END)
            self.ozet.insert(tk.END, f"Başlangıç: {self.baslangic.get()}\n")
            self.ozet.insert(tk.END, f"Bitiş: {self.bitis.get()}\n")
            self.ozet.insert(tk.END, f"Toplam Gelir: {gelir:,.2f} ₺\n")
            self.ozet.insert(tk.END, f"Toplam Gider: {gider:,.2f} ₺\n")
            self.ozet.insert(tk.END, f"Net Bakiye: {bakiye:,.2f} ₺\n")
        except Exception as hata:
            messagebox.showerror("Hata", str(hata))

    def disa_aktar(self):
        yol = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Dosyası", "*.csv")])
        if yol:
            self.db.export_csv(yol)
            messagebox.showinfo("Başarılı", f"Rapor dışa aktarıldı: {yol}")

    def excel_aktar(self):
        yol = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Dosyası", "*.xlsx")])
        if not yol:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "İşlemler"
        ws.append(["id", "tarih", "tur", "kategori", "aciklama", "tutar"])
        for satir in self.db.tum_islemler():
            ws.append(satir)
        wb.save(yol)
        messagebox.showinfo("Başarılı", f"Excel raporu kaydedildi: {yol}")
