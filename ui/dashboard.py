from tkinter import messagebox, ttk

import customtkinter as ctk

from database import normalize_date
from ui.utils import (
    para_formatla,
    tarih_bind,
    treeview_tema_uygula,
    tutar_bind,
    tutar_oku,
)


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
            self.tutar.insert(0, para_formatla(float(islem[5]), sembol=False))
        except (ValueError, TypeError):
            self.tutar.insert(0, str(islem[5]))
        self.tutar.pack(pady=8)
        tutar_bind(self.tutar)

        self.etiketler = ctk.CTkEntry(self, width=300, placeholder_text="Etiketler (virgülle ayır)")
        if len(islem) > 6 and islem[6]:
            self.etiketler.insert(0, islem[6])
        self.etiketler.pack(pady=8)

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
                self.etiketler.get().strip(),
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
        if isinstance(deger, float):
            deger_text = para_formatla(deger)
        elif isinstance(deger, int):
            deger_text = str(deger)
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
            font=("Segoe UI", 28, "bold"),
            text_color="#5eead4",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 0))

        # Aktif kullanıcı
        kullanici_adi = self.db.ayar_oku("aktif_kullanici_adi", "")
        ctk.CTkLabel(
            self,
            text=f"👤 {kullanici_adi}",
            font=("Segoe UI", 11),
            text_color="#64748b",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 10))

        gelir = self.db.toplam_gelir()
        gider = self.db.toplam_gider()
        bakiye = self.db.bakiye()

        self.kart(2, 0, "💰", "Toplam Gelir", gelir)
        self.kart(2, 1, "💸", "Toplam Gider", gider)
        self.kart(3, 0, "🏦", "Bakiye", bakiye)
        self.kart(3, 1, "📄", "İşlem Sayısı", self.db.tum_islem_sayisi())

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
                row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(5, 0)
            )
            uyari_text = "⚠️ Bütçe Aşımı: " + ", ".join(
                f"{b['kategori']} ({para_formatla(b['kalan'], ondalik=0)})"
                for b in asan_kategoriler
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
                row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(5, 0)
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

        # Bütçe ilerleme çubukları
        if butce_durum:
            progres_row = 5 if asan_kategoriler or yaklasan else 4
            progres_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#134e4a")
            progres_frame.grid(
                row=progres_row, column=0, columnspan=2, sticky="ew", padx=20, pady=(5, 0)
            )
            ctk.CTkLabel(
                progres_frame,
                text="📊 Bütçe Durumu",
                font=("Segoe UI", 14, "bold"),
                text_color="#5eead4",
            ).pack(pady=(8, 4))

            for b in butce_durum[:5]:
                oran = min(b["harcanan"] / b["butce"] * 100, 100) if b["butce"] > 0 else 0
                renk = "#ef4444" if oran > 90 else "#f59e0b" if oran > 70 else "#22c55e"
                bar_frame = ctk.CTkFrame(progres_frame, fg_color="transparent")
                bar_frame.pack(fill="x", padx=15, pady=2)
                ctk.CTkLabel(bar_frame, text=b["kategori"], font=("Segoe UI", 11), width=80, anchor="w").pack(side="left")
                bar_bg = ctk.CTkFrame(bar_frame, height=14, fg_color="#1e293b", corner_radius=7)
                bar_bg.pack(side="left", fill="x", expand=True, padx=5)
                bar_fill = ctk.CTkFrame(bar_bg, height=14, fg_color=renk, corner_radius=7)
                bar_fill.place(relx=0, rely=0, relheight=1, relwidth=min(oran / 100, 1))
                ctk.CTkLabel(bar_frame, text=f"%{int(oran)}", font=("Segoe UI", 10), width=40).pack(side="left")
                ctk.CTkLabel(bar_frame, text=f"{para_formatla(b['harcanan'], sembol=False, ondalik=0)}/{para_formatla(b['butce'], ondalik=0)}", font=("Segoe UI", 10), width=120, text_color="#94a3b8").pack(side="left")

        # ARAMA / FİLTRE
        arama_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#134e4a")
        arama_frame.grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 5)
        )
        arama_frame.grid_columnconfigure(0, weight=1)

        self.arama_entry = ctk.CTkEntry(
            arama_frame, placeholder_text="🔍 Kategori, açıklama, etiket veya tutar ara..."
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

        # Bugün / Bu hafta butonları
        self.btn_bugun = ctk.CTkButton(
            arama_frame, text="📅 Bugün", width=70, height=32,
            font=("Segoe UI", 11), fg_color="#0d9488",
            command=lambda: self._filtrele("bugun"),
        )
        self.btn_bugun.grid(row=0, column=3, padx=(2, 2), pady=8)

        self.btn_hafta = ctk.CTkButton(
            arama_frame, text="📆 Bu Hafta", width=85, height=32,
            font=("Segoe UI", 11), fg_color="#0d9488",
            command=lambda: self._filtrele("hafta"),
        )
        self.btn_hafta.grid(row=0, column=4, padx=(2, 5), pady=8)

        self.btn_tumu = ctk.CTkButton(
            arama_frame, text="📋 Tümü", width=60, height=32,
            font=("Segoe UI", 11), fg_color="#475569",
            command=lambda: self._filtrele("tumu"),
        )
        self.btn_tumu.grid(row=0, column=5, padx=(2, 10), pady=8)

        if arama_metni:
            self.arama_entry.insert(0, arama_metni)

        # TABLO
        tablo_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#134e4a")
        tablo_frame.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(
            tablo_frame, text="Son İşlemler", font=("Segoe UI", 20, "bold")
        ).pack(pady=10)

        kolonlar = ("ID", "Tarih", "Tür", "Kategori", "Açıklama", "Tutar", "Etiket")

        treeview_tema_uygula()
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
        # Hızlı İşlem Butonları
        # ==========================
        self.btn_hizli_gelir = ctk.CTkButton(
            buton_frame,
            text="💰 + Gelir",
            fg_color="#2e8b57",
            hover_color="#1a4730",
            command=self._hizli_gelir,
        )
        self.btn_hizli_gelir.pack(side="left", padx=8)

        self.btn_hizli_gider = ctk.CTkButton(
            buton_frame,
            text="💸 + Gider",
            fg_color="#c0392b",
            hover_color="#8b1a1a",
            command=self._hizli_gider,
        )
        self.btn_hizli_gider.pack(side="left", padx=8)

        # ==========================
        # Dışa Aktar Butonları (Rapor birleştirildi)
        # ==========================
        export_frame = ctk.CTkFrame(tablo_frame, fg_color="transparent")
        export_frame.pack(pady=(5, 5))

        ctk.CTkLabel(
            export_frame,
            text="📤 Dışa Aktar:",
            font=("Segoe UI", 12),
            text_color="#94a3b8",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            export_frame,
            text="CSV",
            width=70,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#475569",
            command=self._csv_aktar,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            export_frame,
            text="Excel",
            width=70,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#166534",
            command=self._excel_aktar,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            export_frame,
            text="PDF",
            width=70,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#991b1b",
            command=self._pdf_aktar,
        ).pack(side="left", padx=3)

        ctk.CTkLabel(
            export_frame,
            text="   📥 İçe Aktar:",
            font=("Segoe UI", 12),
            text_color="#94a3b8",
        ).pack(side="left", padx=(12, 8))

        ctk.CTkButton(
            export_frame,
            text="CSV/Excel",
            width=90,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#0d9488",
            command=self._ice_aktar,
        ).pack(side="left", padx=3)

    # ==========================
    # Dışa Aktar Metotları
    # ==========================

    def _csv_aktar(self):
        from tkinter import filedialog, messagebox
        import csv

        yol = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")]
        )
        if not yol:
            return
        try:
            with open(yol, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Tarih", "Tür", "Kategori", "Açıklama", "Tutar", "Etiket"])
                for satir in self.db.islem_ara():
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(str(satir[1]), "%Y-%m-%d")
                        tarih_goster = dt.strftime("%d.%m.%Y")
                    except Exception:
                        tarih_goster = satir[1]
                    etiket = satir[6] if len(satir) > 6 else ""
                    writer.writerow([satir[0], tarih_goster, satir[2], satir[3], satir[4], satir[5], etiket])
            messagebox.showinfo("Başarılı", f"CSV dışa aktarıldı:\n{yol}")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _excel_aktar(self):
        from tkinter import filedialog, messagebox

        try:
            from openpyxl import Workbook
        except ImportError:
            messagebox.showerror("Hata", "openpyxl kütüphanesi gerekli.")
            return

        yol = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")]
        )
        if not yol:
            return
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "İşlemler"
            ws.append(["ID", "Tarih", "Tür", "Kategori", "Açıklama", "Tutar", "Etiket"])
            for satir in self.db.islem_ara():
                ws.append(list(satir))
            wb.save(yol)
            messagebox.showinfo("Başarılı", f"Excel dışa aktarıldı:\n{yol}")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _pdf_aktar(self):
        from tkinter import filedialog, messagebox

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
            )
        except ImportError:
            messagebox.showerror("Hata", "reportlab kütüphanesi gerekli.")
            return

        yol = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
        )
        if not yol:
            return
        try:
            doc = SimpleDocTemplate(yol, pagesize=A4, topMargin=20 * mm)
            styles = getSampleStyleSheet()
            elemanlar = []
            elemanlar.append(Paragraph("FINEding — İşlem Raporu", styles["Title"]))
            elemanlar.append(Spacer(1, 10 * mm))

            veri = [["ID", "Tarih", "Tür", "Kategori", "Açıklama", "Tutar", "Etiket"]]
            for satir in self.db.islem_ara():
                veri.append([str(s) for s in satir])

            tablo = Table(veri)
            tablo.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ])
            )
            elemanlar.append(tablo)
            doc.build(elemanlar)
            messagebox.showinfo("Başarılı", f"PDF dışa aktarıldı:\n{yol}")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _ice_aktar(self):
        """CSV veya Excel dosyasından toplu işlem içe aktarır."""
        from tkinter import filedialog

        yol = filedialog.askopenfilename(
            filetypes=[("CSV veya Excel", "*.csv *.xlsx"), ("CSV", "*.csv"), ("Excel", "*.xlsx")]
        )
        if not yol:
            return

        beklenen = (
            "Beklenen sütunlar: Tarih, Tür (Gelir/Gider), Kategori, "
            "Açıklama, Tutar, Etiket (opsiyonel)."
        )
        if not messagebox.askyesno(
            "İçe Aktar",
            f"'{yol}' dosyasındaki işlemler eklenecek. Devam edilsin mi?\n\n{beklenen}",
        ):
            return

        try:
            if yol.lower().endswith(".xlsx"):
                eklenen = self.db.import_excel(yol)
            else:
                eklenen = self.db.import_csv(yol)
            messagebox.showinfo("Başarılı", f"{eklenen} işlem içe aktarıldı.")
            self.yenile()
        except Exception as e:
            messagebox.showerror("Hata", f"İçe aktarma başarısız: {e}")

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

    def _hizli_islem(self, tur):
        """Hızlı işlem ekleme penceresi açar."""
        from datetime import datetime
        from ui.utils import tutar_bind, tutar_oku

        pencere = ctk.CTkToplevel(self)
        pencere.title(f"Hızlı {tur} Ekle")
        pencere.geometry("380x280")
        pencere.resizable(False, False)
        pencere.transient(self.winfo_toplevel())
        pencere.grab_set()
        pencere.lift()
        pencere.focus_force()

        ctk.CTkLabel(
            pencere,
            text=f"{'💰' if tur == 'Gelir' else '💸'} Hızlı {tur} Ekle",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=15)

        tutar_entry = ctk.CTkEntry(pencere, width=280, placeholder_text="Tutar (₺)", font=("Segoe UI", 16))
        tutar_entry.pack(pady=8)
        tutar_bind(tutar_entry)
        tutar_entry.focus()

        aciklama_entry = ctk.CTkEntry(pencere, width=280, placeholder_text="Açıklama (opsiyonel)", font=("Segoe UI", 13))
        aciklama_entry.pack(pady=8)

        def kaydet():
            try:
                t = tutar_oku(tutar_entry)
                if t <= 0:
                    messagebox.showwarning("Uyarı", "Tutar 0'dan büyük olmalı.")
                    return
                aciklama = aciklama_entry.get().strip() or None
                bugun = datetime.now().strftime("%d.%m.%Y")
                if tur == "Gelir":
                    self.db.gelir_ekle(bugun, "Diğer", aciklama, t)
                else:
                    self.db.gider_ekle(bugun, "Diğer", aciklama, t)
                messagebox.showinfo("Başarılı", f"{tur} eklendi: {para_formatla(t)}")
                pencere.destroy()
                self.yenile()
            except ValueError:
                messagebox.showerror("Hata", "Geçerli bir tutar giriniz.")
            except Exception as e:
                messagebox.showerror("Hata", str(e))

        ctk.CTkButton(
            pencere,
            text=f"💾 {tur} Ekle",
            width=200,
            fg_color="#2e8b57" if tur == "Gelir" else "#c0392b",
            command=kaydet,
        ).pack(pady=15)

        pencere.bind("<Return>", lambda e: kaydet())

    def _hizli_gelir(self):
        self._hizli_islem("Gelir")

    def _hizli_gider(self):
        self._hizli_islem("Gider")

    def _filtrele(self, mod):
        """Bugün/Bu hafta/Tümü filtresi uygular."""
        self.tablo.delete(*self.tablo.get_children())
        if mod == "bugun":
            islemler = self.db.gunluk_islemler()
        elif mod == "hafta":
            islemler = self.db.haftalik_islemler()
        else:
            islemler = self.db.islem_ara()
        for satir in islemler:
            self.tablo.insert("", "end", values=satir)
