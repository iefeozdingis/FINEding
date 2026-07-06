from tkinter import ttk, messagebox
import customtkinter as ctk


class IslemDuzenlemePenceresi(ctk.CTkToplevel):

    def __init__(self, parent, db, islem):
        super().__init__(parent)
        self.db = db
        self.islem = islem
        self.title("İşlem Düzenle")
        self.geometry("420x360")
        self.resizable(False, False)

        ctk.CTkLabel(self, text="İşlem Düzenle", font=("Segoe UI", 22, "bold")).pack(pady=16)

        self.tarih = ctk.CTkEntry(self, width=300, placeholder_text="Tarih")
        self.tarih.insert(0, islem[1])
        self.tarih.pack(pady=8)

        self.tur = ctk.CTkComboBox(self, width=300, values=["Gelir", "Gider"])
        self.tur.set(islem[2])
        self.tur.pack(pady=8)

        self.kategori = ctk.CTkEntry(self, width=300, placeholder_text="Kategori")
        self.kategori.insert(0, islem[3])
        self.kategori.pack(pady=8)

        self.aciklama = ctk.CTkEntry(self, width=300, placeholder_text="Açıklama")
        self.aciklama.insert(0, islem[4])
        self.aciklama.pack(pady=8)

        self.tutar = ctk.CTkEntry(self, width=300, placeholder_text="Tutar")
        self.tutar.insert(0, str(islem[5]))
        self.tutar.pack(pady=8)

        ctk.CTkButton(self, text="💾 Kaydet", width=220, command=self.kaydet).pack(pady=16)

    def kaydet(self):
        try:
            self.db.guncelle_islem(self.islem[0], self.tarih.get(), self.tur.get(), self.kategori.get(), self.aciklama.get(), float(self.tutar.get()))
            messagebox.showinfo("Başarılı", "İşlem güncellendi.")
            self.destroy()
        except Exception as hata:
            messagebox.showerror("Hata", str(hata))


class Dashboard(ctk.CTkFrame):

    def __init__(self, parent, db):
        super().__init__(parent)

        self.db = db

        self.grid_columnconfigure((0, 1), weight=1)

        self.yenile()

    # ==========================
    # Kart Oluştur
    # ==========================

    def kart(self, row, col, icon, baslik, deger):

        frame = ctk.CTkFrame(self, height=150)

        frame.grid(
            row=row,
            column=col,
            padx=15,
            pady=15,
            sticky="nsew"
        )

        frame.grid_propagate(False)

        ctk.CTkLabel(
            frame,
            text=icon,
            font=("Segoe UI Emoji", 34)
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            frame,
            text=baslik,
            font=("Segoe UI", 16, "bold")
        ).pack()

        ctk.CTkLabel(
            frame,
            text=f"{deger:,.2f} ₺",
            font=("Segoe UI", 24, "bold")
        ).pack(pady=(5, 15))

    # ==========================
    # Dashboard Yenile
    # ==========================

    def yenile(self):

        for widget in self.winfo_children():
            widget.destroy()

        self.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self,
            text="📊 Dashboard",
            font=("Segoe UI", 30, "bold")
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=20,
            pady=20
        )

        gelir = self.db.toplam_gelir()
        gider = self.db.toplam_gider()
        bakiye = self.db.bakiye()

        self.kart(
            1,
            0,
            "💰",
            "Toplam Gelir",
            gelir
        )

        self.kart(
            1,
            1,
            "💸",
            "Toplam Gider",
            gider
        )

        self.kart(
            2,
            0,
            "🏦",
            "Bakiye",
            bakiye
        )

        self.kart(
            2,
            1,
            "📄",
            "İşlem Sayısı",
            len(self.db.tum_islemler())
        )

        # ==========================
        # TABLO
        # ==========================

        tablo_frame = ctk.CTkFrame(self)

        tablo_frame.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=20,
            pady=20
        )

        ctk.CTkLabel(
            tablo_frame,
            text="Son İşlemler",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=10)

        kolonlar = (
            "ID",
            "Tarih",
            "Tür",
            "Kategori",
            "Açıklama",
            "Tutar"
        )

        self.tablo = ttk.Treeview(
            tablo_frame,
            columns=kolonlar,
            show="headings",
            height=10
        )

        for kolon in kolonlar:

            self.tablo.heading(
                kolon,
                text=kolon
            )

            self.tablo.column(
                kolon,
                width=120,
                anchor="center"
            )

        self.tablo.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        for satir in self.db.tum_islemler():

            self.tablo.insert(
                "",
                "end",
                values=satir
            )

        buton_frame = ctk.CTkFrame(tablo_frame)
        buton_frame.pack(pady=10)

        self.btn_duzenle = ctk.CTkButton(
            buton_frame,
            text="✏ Düzenle",
            command=self.seciliyi_duzenle
        )
        self.btn_duzenle.pack(side="left", padx=8)

        self.btn_sil = ctk.CTkButton(
            buton_frame,
            text="🗑 Sil",
            fg_color="red",
            hover_color="#b30000",
            command=self.seciliyi_sil
        )
        self.btn_sil.pack(side="left", padx=8)

    # ==========================
    # Seçili İşlemi Sil
    # ==========================

    def seciliyi_duzenle(self):
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen önce bir işlem seçiniz.")
            return
        veri = self.tablo.item(secili[0])["values"]
        IslemDuzenlemePenceresi(self, self.db, veri).grab_set()

    def seciliyi_sil(self):

        secili = self.tablo.selection()

        if not secili:

            messagebox.showwarning(
                "Uyarı",
                "Lütfen önce bir işlem seçiniz."
            )

            return

        veri = self.tablo.item(secili[0])["values"]

        cevap = messagebox.askyesno(
            "Sil",
            "Seçili işlem silinsin mi?"
        )

        if not cevap:
            return

        self.db.sil(veri[0])

        self.yenile()