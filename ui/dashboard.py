from tkinter import messagebox, ttk

import customtkinter as ctk

from database import normalize_date
from ui.utils import tarih_bind, tutar_bind, tutar_oku


class IslemDuzenlemePenceresi(ctk.CTkToplevel):
    def __init__(self, parent, db, islem):
        super().__init__(parent)
        self.db = db
        self.islem = islem
        self.title("İşlem Düzenle")
        self.geometry("420x360")
        self.resizable(False, False)

        # Modal: arkaya kaçmaz, ana sayfaya tıklanamaz
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(self, text="İşlem Düzenle", font=("Segoe UI", 22, "bold")).pack(
            pady=16
        )

        self.tarih = ctk.CTkEntry(self, width=300, placeholder_text="Tarih")
        # Tarihi ISO'dan GG.AA.YYYY'e çevir
        try:
            from datetime import datetime

            dt = datetime.strptime(islem[1], "%Y-%m-%d")
            self.tarih.insert(0, dt.strftime("%d.%m.%Y"))
        except ValueError:
            self.tarih.insert(0, islem[1])
        self.tarih.pack(pady=8)
        tarih_bind(self.tarih)

        self.tur = ctk.CTkComboBox(self, width=300, values=["Gelir", "Gider"])
        self.tur.set(islem[2])
        self.tur.pack(pady=8)
        # Tür değişince kategori listesini güncelle
        self.tur.configure(command=self._tur_degisti)

        self.kategori = ctk.CTkComboBox(
            self,
            width=300,
            values=self._kategoriler(islem[2]),
            button_color="#475569",
            button_hover_color="#334155",
        )
        self.kategori.set(islem[3])
        self.kategori.pack(pady=8)

        self.aciklama = ctk.CTkEntry(self, width=300, placeholder_text="Açıklama")
        self.aciklama.insert(0, islem[4])
        self.aciklama.pack(pady=8)

        self.tutar = ctk.CTkEntry(self, width=300, placeholder_text="Tutar")
        # Tutarı formatlı göster
        try:
            t = float(islem[5])
            self.tutar.insert(
                0, f"{t:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        except (ValueError, TypeError):
            self.tutar.insert(0, str(islem[5]))
        self.tutar.pack(pady=8)
        tutar_bind(self.tutar)

        ctk.CTkButton(self, text="💾 Kaydet", width=220, command=self.kaydet).pack(
            pady=16
        )

    def _kategoriler(self, tur=None):
        from ui.gelir import VARSAYILAN_GELIR_KATEGORILER
        from ui.gider import VARSAYILAN_GIDER_KATEGORILER

        if tur is None:
            tur = self.tur.get()
        if tur == "Gelir":
            ozel = self.db.kategorileri_getir("Gelir")
            kategoriler = VARSAYILAN_GELIR_KATEGORILER + [
                k for k in ozel if k not in VARSAYILAN_GELIR_KATEGORILER
            ]
        else:
            ozel = self.db.kategorileri_getir("Gider")
            kategoriler = VARSAYILAN_GIDER_KATEGORILER + [
                k for k in ozel if k not in VARSAYILAN_GIDER_KATEGORILER
            ]
        return kategoriler

    def _tur_degisti(self, secim):
        self.kategori.configure(values=self._kategoriler(secim))
        varsayilan = self._kategoriler(secim)[0]
        self.kategori.set(varsayilan)

    def kaydet(self):
        # Validate date before updating
        try:
            tarih_iso = normalize_date(self.tarih.get())
        except Exception as e:
            messagebox.showerror("Hata", f"Geçersiz tarih: {e}")
            return

        try:
            self.db.guncelle_islem(
                self.islem[0],
                tarih_iso,
                self.tur.get(),
                self.kategori.get(),
                self.aciklama.get(),
                tutar_oku(self.tutar),
            )
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

    # Kart renkleri
    KART_RENKLER = {
        "💰": ("#1a472a", "#2e8b57"),  # Gelir - yeşil
        "💸": ("#6b1c1c", "#c0392b"),  # Gider - kırmızı
        "🏦": ("#134e4a", "#14b8a6"),  # Bakiye - teal
        "📄": ("#4a3a0a", "#d4a017"),  # İşlem - altın
    }

    def kart(self, row, col, icon, baslik, deger):
        koyu, acik = self.KART_RENKLER.get(icon, ("#2d2d2d", "#555555"))

        frame = ctk.CTkFrame(
            self,
            height=150,
            corner_radius=16,
            fg_color=koyu,
            border_width=1,
            border_color=acik,
        )
        frame.grid(row=row, column=col, padx=12, pady=10, sticky="nsew")
        frame.grid_propagate(False)

        # İkon
        ctk.CTkLabel(frame, text=icon, font=("Segoe UI Emoji", 36)).pack(pady=(18, 2))

        # Başlık
        ctk.CTkLabel(
            frame, text=baslik, font=("Segoe UI", 13), text_color="#94a3b8"
        ).pack()

        # Değer - para formatı
        if isinstance(deger, (int, float)):
            deger_text = f"{deger:,.2f} ₺"
        else:
            deger_text = str(deger)
        ctk.CTkLabel(
            frame, text=deger_text, font=("Segoe UI", 24, "bold"), text_color="#ffffff"
        ).pack(pady=(2, 18))

        # Hover efekti + tıklama
        def on_enter(e, f=frame, a=acik):
            f.configure(border_width=2, border_color="#ffffff")

        def on_leave(e, f=frame, a=acik):
            f.configure(border_width=1, border_color=a)

        def on_click(e, icon=icon):
            top = self.winfo_toplevel()
            if icon == "💰" and hasattr(top, "gelir_ac"):
                top.gelir_ac()
            elif icon == "💸" and hasattr(top, "gider_ac"):
                top.gider_ac()

        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)
        frame.bind("<Button-1>", on_click)
        for child in frame.winfo_children():
            child.bind("<Button-1>", on_click)

    # ==========================
    # Dashboard Yenile
    # ==========================

    def yenile(self):
        # Mevcut arama/filtre değerlerini sakla
        arama_metni = ""
        tur_secili = "Tümü"
        if hasattr(self, "arama_entry") and self.arama_entry.winfo_exists():
            arama_metni = self.arama_entry.get()
        if hasattr(self, "tur_filtre") and self.tur_filtre.winfo_exists():
            tur_secili = self.tur_filtre.get()

        for widget in self.winfo_children():
            widget.destroy()

        self.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self,
            text="📊  Dashboard",
            font=("Segoe UI", 30, "bold"),
            text_color="#5eead4",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))

        # Aktif kullanıcı
        kullanici_adi = self.db.ayar_oku("aktif_kullanici_adi", "")
        ctk.CTkLabel(
            self,
            text=f"👤 {kullanici_adi}",
            font=("Segoe UI", 12),
            text_color="#2dd4bf",
        ).grid(row=0, column=1, sticky="e", padx=20, pady=(20, 5))

        gelir = self.db.toplam_gelir()
        gider = self.db.toplam_gider()
        bakiye = self.db.bakiye()

        self.kart(1, 0, "💰", "Toplam Gelir", gelir)
        self.kart(1, 1, "💸", "Toplam Gider", gider)
        self.kart(2, 0, "🏦", "Bakiye", bakiye)
        self.kart(2, 1, "📄", "İşlem Sayısı", self.db.tum_islem_sayisi())

        # Bu ay bütçe uyarısı
        from datetime import datetime

        simdi = datetime.now()
        butce_durum = self.db.butce_durumu(simdi.month, simdi.year)
        asan_kategoriler = [b for b in butce_durum if b["kalan"] < 0]
        yaklasan = [
            b
            for b in butce_durum
            if 0 <= b["kalan"] < b["butce"] * 0.2 and b["kalan"] >= 0
        ]
        if asan_kategoriler:
            uyari_frame = ctk.CTkFrame(self, fg_color="#8B0000")
            uyari_frame.grid(
                row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(5, 0)
            )
            uyari_text = "⚠️ Bütçe Aşımı: " + ", ".join(
                f"{b['kategori']} ({b['kalan']:,.0f} ₺)" for b in asan_kategoriler
            )
            ctk.CTkLabel(
                uyari_frame,
                text=uyari_text,
                font=("Segoe UI", 13, "bold"),
                text_color="white",
            ).pack(pady=8)

        # Erken uyarı (bütçeye yaklaşanlar)
        if yaklasan and not asan_kategoriler:
            uyari_frame = ctk.CTkFrame(self, fg_color="#7c5e00")
            uyari_frame.grid(
                row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(5, 0)
            )
            uyari_text = "🟡 Bütçeye Yaklaşıyor: " + ", ".join(
                f"{b['kategori']} (%{int((1-b['kalan']/b['butce'])*100)})"
                for b in yaklasan
            )
            ctk.CTkLabel(
                uyari_frame,
                text=uyari_text,
                font=("Segoe UI", 13, "bold"),
                text_color="white",
            ).pack(pady=8)

        # ARAMA / FİLTRE
        arama_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#134e4a")
        arama_frame.grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 5)
        )
        arama_frame.grid_columnconfigure(0, weight=1)

        self.arama_entry = ctk.CTkEntry(
            arama_frame, placeholder_text="🔍 Kategori, açıklama veya tutar ara..."
        )
        self.arama_entry.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=8)
        self.arama_entry.bind("<Return>", lambda e: self.yenile())

        self.ara_btn = ctk.CTkButton(
            arama_frame,
            text="🔍 Ara",
            width=70,
            height=32,
            fg_color="#0d9488",
            command=self.yenile,
        )
        self.ara_btn.grid(row=0, column=2, padx=(5, 10), pady=8)

        self.tur_filtre = ctk.CTkComboBox(
            arama_frame,
            width=120,
            values=["Tümü", "Gelir", "Gider"],
            command=lambda _: self.yenile(),
        )
        self.tur_filtre.set(tur_secili)
        self.tur_filtre.grid(row=0, column=1, padx=(5, 10), pady=8)

        if arama_metni:
            self.arama_entry.insert(0, arama_metni)

        # TABLO
        tablo_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#134e4a")
        tablo_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(
            tablo_frame, text="Son İşlemler", font=("Segoe UI", 20, "bold")
        ).pack(pady=10)

        kolonlar = ("ID", "Tarih", "Tür", "Kategori", "Açıklama", "Tutar")

        self.tablo = ttk.Treeview(
            tablo_frame, columns=kolonlar, show="headings", height=10
        )

        for kolon in kolonlar:
            self.tablo.heading(kolon, text=kolon)
            self.tablo.column(kolon, width=120, anchor="center")

        self.tablo.pack(fill="both", expand=True, padx=10, pady=10)

        # Filtre uygula
        tur = "" if tur_secili == "Tümü" else tur_secili
        for satir in self.db.islem_ara(arama_metni, tur):
            self.tablo.insert("", "end", values=satir)

        buton_frame = ctk.CTkFrame(tablo_frame)
        buton_frame.pack(pady=10)

        self.btn_duzenle = ctk.CTkButton(
            buton_frame, text="✏ Düzenle", command=self.seciliyi_duzenle
        )
        self.btn_duzenle.pack(side="left", padx=8)

        self.btn_sil = ctk.CTkButton(
            buton_frame,
            text="🗑 Sil",
            fg_color="red",
            hover_color="#b30000",
            command=self.seciliyi_sil,
        )
        self.btn_sil.pack(side="left", padx=8)

        self.btn_geri_al = ctk.CTkButton(
            buton_frame,
            text="↩ Geri Al",
            fg_color="#555",
            hover_color="#333",
            command=self.geri_al,
        )
        self.btn_geri_al.pack(side="left", padx=8)

        self.btn_toplu_sil = ctk.CTkButton(
            buton_frame,
            text="🗑 Toplu Sil",
            fg_color="#8B0000",
            hover_color="#660000",
            command=self.toplu_sil,
        )
        self.btn_toplu_sil.pack(side="left", padx=8)

    # ==========================
    # Seçili İşlemi Sil
    # ==========================

    def seciliyi_duzenle(self):
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen önce bir işlem seçiniz.")
            return
        veri = self.tablo.item(secili[0])["values"]
        pencere = IslemDuzenlemePenceresi(self, self.db, veri)
        self.wait_window(pencere)
        self.yenile()

    def seciliyi_sil(self):
        secili = self.tablo.selection()

        if not secili:
            messagebox.showwarning("Uyarı", "Lütfen önce bir işlem seçiniz.")

            return

        veri = self.tablo.item(secili[0])["values"]

        cevap = messagebox.askyesno("Sil", "Seçili işlem silinsin mi?")

        if not cevap:
            return

        self.db.sil(veri[0])

        self.yenile()

    def geri_al(self):
        if self.db.geri_al():
            messagebox.showinfo("Başarılı", "Son silinen işlem geri getirildi.")
            self.yenile()
        else:
            messagebox.showwarning("Uyarı", "Geri alınacak işlem bulunamadı.")

    def toplu_sil(self):
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning(
                "Uyarı", "Ctrl+tıklama ile birden fazla satır seçin."
            )
            return
        if not messagebox.askyesno("Toplu Sil", f"{len(secili)} işlem silinsin mi?"):
            return
        for s in secili:
            veri = self.tablo.item(s)["values"]
            self.db.sil(veri[0])
        self.yenile()
        messagebox.showinfo("Başarılı", f"{len(secili)} işlem silindi.")
