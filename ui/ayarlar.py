import customtkinter as ctk
from tkinter import filedialog, messagebox


class AyarlarSayfasi(ctk.CTkFrame):

    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent)
        self.db = db
        self.dashboard_callback = dashboard_callback
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="⚙️ Ayarlar", font=("Segoe UI", 28, "bold")).pack(pady=20)

        ctk.CTkLabel(self, text="Tema", font=("Segoe UI", 14)).pack(pady=(10, 4))
        self.tema = ctk.CTkComboBox(self, width=260, values=["dark", "light", "system"])
        self.tema.set(self.db.ayar_oku("tema", "dark"))
        self.tema.pack(pady=8)

        ctk.CTkButton(self, text="💾 Ayarları Kaydet", width=220, command=self.kaydet).pack(pady=16)
        ctk.CTkButton(self, text="🗂 Yedek Oluştur", width=220, command=self.yedek_olustur).pack(pady=8)
        ctk.CTkButton(self, text="♻️ Yedeği Geri Yükle", width=220, command=self.yedek_geri_yukle).pack(pady=8)

    def kaydet(self):
        self.db.ayar_kaydet("tema", self.tema.get())
        ctk.set_appearance_mode(self.tema.get())
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")

    def yedek_olustur(self):
        yol = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("Veritabanı", "*.db")])
        if yol:
            self.db.yedekle(yol)
            messagebox.showinfo("Başarılı", f"Yedek oluşturuldu: {yol}")

    def yedek_geri_yukle(self):
        yol = filedialog.askopenfilename(defaultextension=".db", filetypes=[("Veritabanı", "*.db")])
        if yol:
            self.db.geri_yukle(yol)
            messagebox.showinfo("Başarılı", "Yedek geri yüklendi.")
