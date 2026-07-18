"""Planlama & Takip sayfası — düzenlenebilir tablo, borç/alacak takibi."""

from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from ui import tema
from ui.utils import (
    modal_yap,
    para_formatla,
    para_parse,
    tarih_bind,
    treeview_tema_uygula,
    tutar_bind,
    tutar_oku,
)


class PlanlamaSayfasi(ctk.CTkFrame):
    # Global aramadan derin bağlantı için sekme adı eşlemesi
    SEKME_ADLARI = {
        "planlama": "📋 Aylık Planlama",
        "borc": "💳 Borçlar & Alacaklar",
        "tekrarlayan": "🔄 Tekrarlayan",
        "tasarruf": "🎯 Tasarruf Hedefleri",
    }

    def __init__(self, parent, db, dashboard_callback=None,
                 baslangic_sekme=None, secili_kayit=None):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.dashboard_callback = dashboard_callback
        treeview_tema_uygula()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sekmeli yapı
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=16,
            fg_color=tema.KART,
            segmented_button_fg_color="#0f766e",
            segmented_button_selected_color="#0d9488",
            segmented_button_unselected_color="#134e4a",
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        self.tabview.add("📋 Aylık Planlama")
        self.tabview.add("💳 Borçlar & Alacaklar")
        self.tabview.add("🔄 Tekrarlayan")
        self.tabview.add("🎯 Tasarruf Hedefleri")

        self._aylik_planlama_olustur()
        self._borc_alacak_olustur()
        self._tekrarlayan_olustur()
        self._tasarruf_olustur()

        # Derin bağlantı: global aramadan gelindiyse ilgili sekmeyi aç ve
        # kaydı seç (önceden hep ilk sekme açılıyor, kayıt seçili gelmiyordu)
        if baslangic_sekme in self.SEKME_ADLARI:
            try:
                self.tabview.set(self.SEKME_ADLARI[baslangic_sekme])
            except Exception:
                pass
            if baslangic_sekme == "borc" and secili_kayit is not None:
                self.after(100, lambda: self._borc_sec(secili_kayit))

    def _borc_sec(self, borc_id):
        """Verilen borç kaydını tabloda seçili hale getirir."""
        for item in self.b_tablo.get_children():
            deger = self.b_tablo.item(item)["values"]
            if deger and str(deger[0]) == str(borc_id):
                self.b_tablo.selection_set(item)
                self.b_tablo.see(item)
                break

    # =========================================
    # AYLIK PLANLAMA SEKMESİ
    # =========================================

    def _aylik_planlama_olustur(self):
        tab = self.tabview.tab("📋 Aylık Planlama")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        # Üst kontrol barı
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        bar.grid_columnconfigure(5, weight=1)

        simdi = datetime.now()
        ctk.CTkLabel(bar, text="Ay:", font=("Segoe UI", 14)).grid(
            row=0, column=0, padx=(0, 5)
        )
        self.p_ay = ctk.CTkEntry(bar, width=50, font=("Segoe UI", 14))
        self.p_ay.insert(0, str(simdi.month))
        self.p_ay.grid(row=0, column=1, padx=(0, 10))

        ctk.CTkLabel(bar, text="Yıl:", font=("Segoe UI", 14)).grid(
            row=0, column=2, padx=(0, 5)
        )
        self.p_yil = ctk.CTkEntry(bar, width=70, font=("Segoe UI", 14))
        self.p_yil.insert(0, str(simdi.year))
        self.p_yil.grid(row=0, column=3, padx=(0, 10))

        ctk.CTkButton(
            bar,
            text="🔄 Göster",
            width=90,
            height=32,
            fg_color="#0d9488",
            command=self._planlama_yenile,
        ).grid(row=0, column=4, padx=(0, 5))

        # Özet
        self.p_ozet = ctk.CTkLabel(
            bar, text="", font=("Segoe UI", 14, "bold"), text_color="#5eead4"
        )
        self.p_ozet.grid(row=0, column=5, sticky="e", padx=(10, 0))

        # Ayraç
        ctk.CTkFrame(tab, height=1, fg_color="#334155").grid(
            row=1, column=0, sticky="ew", padx=15, pady=(5, 0)
        )

        # Buton bar
        btn_bar = ctk.CTkFrame(tab, fg_color="transparent")
        btn_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=5)

        ctk.CTkButton(
            btn_bar,
            text="➕ Satır Ekle",
            width=120,
            height=30,
            fg_color="#2e8b57",
            command=self._satir_ekle,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_bar,
            text="🗑 Seçileni Sil",
            width=120,
            height=30,
            fg_color="#c0392b",
            command=self._satir_sil,
        ).pack(side="left")

        ctk.CTkButton(
            btn_bar,
            text="📋 Planı Gerçeğe Aktar",
            width=180,
            height=30,
            fg_color="#8b5cf6",
            command=self._plani_aktar,
        ).pack(side="right")

        ctk.CTkButton(
            btn_bar,
            text="📝 Önceki Aydan Kopyala",
            width=180,
            height=30,
            fg_color="#0ea5e9",
            command=self._kopyala,
        ).pack(side="right", padx=(0, 8))

        # Düzenlenebilir tablo
        self.p_kolonlar = ("ID", "Kategori", "Tür", "Açıklama", "Tutar")
        self.p_tablo = ttk.Treeview(
            tab, columns=self.p_kolonlar, show="headings", height=12
        )
        self.p_tablo.grid(row=3, column=0, sticky="nsew", padx=15, pady=(5, 15))

        for k in self.p_kolonlar:
            self.p_tablo.heading(k, text=k)
        self.p_tablo.column("ID", width=40, anchor="center")
        self.p_tablo.column("Kategori", width=150, anchor="center")
        self.p_tablo.column("Tür", width=80, anchor="center")
        self.p_tablo.column("Açıklama", width=200, anchor="center")
        self.p_tablo.column("Tutar", width=120, anchor="center")

        # Çift tıklayınca düzenle
        self.p_tablo.bind("<Double-1>", self._hucre_duzenle)
        self._edit_entry = None
        self._edit_id = None
        self._edit_col = None

        self._planlama_yenile()

    def _planlama_yenile(self):
        for item in self.p_tablo.get_children():
            self.p_tablo.delete(item)

        try:
            ay = int(self.p_ay.get())
            yil = int(self.p_yil.get())
        except ValueError:
            return

        for satir in self.db.planlanan_listele(ay, yil):
            self.p_tablo.insert(
                "",
                "end",
                values=(
                    satir[0],
                    satir[3],
                    satir[4],
                    satir[5] or "",
                    para_formatla(satir[6], sembol=False),
                ),
            )

        ozet = self.db.planlanan_ozet(ay, yil)
        net = ozet["Gelir"] - ozet["Gider"]
        self.p_ozet.configure(
            text=f"📥 {para_formatla(ozet['Gelir'], ondalik=0)}  |  "
            f"📤 {para_formatla(ozet['Gider'], ondalik=0)}  |  "
            f"{'✅' if net >= 0 else '🔴'} Net: {para_formatla(net, ondalik=0)}"
        )

    def _satir_ekle(self):
        try:
            ay = int(self.p_ay.get())
            yil = int(self.p_yil.get())
        except ValueError:
            messagebox.showwarning("Uyarı", "Geçerli ay/yıl giriniz.")
            return

        Pencere(self, "Yeni Plan", self._kaydet_yeni, {"ay": ay, "yil": yil})

    def _kaydet_yeni(self, pencere, data):
        self.db.planlanan_ekle(
            data["ay"],
            data["yil"],
            data["kategori"],
            data["tur"],
            data["aciklama"],
            data["tutar"],
        )
        pencere.destroy()
        self._planlama_yenile()

    def _satir_sil(self):
        secili = self.p_tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Silmek için bir satır seçin.")
            return
        veri = self.p_tablo.item(secili[0])["values"]
        if messagebox.askyesno("Sil", "Bu plan silinsin mi?"):
            self.db.planlanan_sil(int(veri[0]))
            self._planlama_yenile()

    def _hucre_duzenle(self, event):
        """Çift tıklanan hücreyi düzenleme moduna al."""
        if self._edit_entry:
            self._edit_uygula()

        bolge = self.p_tablo.identify_region(event.x, event.y)
        if bolge != "cell":
            return

        col = self.p_tablo.identify_column(event.x)
        item = self.p_tablo.identify_row(event.y)
        if not item:
            return

        col_idx = int(col[1]) - 1  # 1-based -> 0-based
        if col_idx == 0:  # ID sütunu düzenlenemez
            return

        veri = self.p_tablo.item(item)["values"]
        self._edit_id = int(veri[0])
        self._edit_col = col_idx

        # Entry oluştur
        x, y, w, h = self.p_tablo.bbox(item, col)
        self._edit_entry = ctk.CTkEntry(
            self.p_tablo,
            width=w,
            height=h,
            font=("Segoe UI", 12),
        )
        self._edit_entry.place(x=x, y=y)
        self._edit_entry.insert(0, str(veri[col_idx]))
        self._edit_entry.focus()
        self._edit_entry.bind("<Return>", lambda e: self._edit_uygula())
        self._edit_entry.bind("<FocusOut>", lambda e: self._edit_uygula())

    def _edit_uygula(self):
        if not self._edit_entry:
            return
        yeni_deger = self._edit_entry.get().strip()
        self._edit_entry.destroy()
        self._edit_entry = None

        # Veritabanından mevcut satırı al
        try:
            ay = int(self.p_ay.get())
            yil = int(self.p_yil.get())
        except ValueError:
            return

        satirlar = self.db.planlanan_listele(ay, yil)
        mevcut = None
        for s in satirlar:
            if s[0] == self._edit_id:
                mevcut = s
                break
        if not mevcut:
            self._planlama_yenile()
            return

        # Güncelle
        if self._edit_col == 1:  # Kategori
            self.db.planlanan_guncelle(
                self._edit_id, yeni_deger, mevcut[4], mevcut[5] or "", mevcut[6]
            )
        elif self._edit_col == 2:  # Tür
            if yeni_deger not in ("Gelir", "Gider"):
                messagebox.showwarning(
                    "Geçersiz tür",
                    "Tür yalnızca 'Gelir' veya 'Gider' olabilir.\n"
                    "Değişiklik kaydedilmedi.",
                )
                self._planlama_yenile()
                return
            self.db.planlanan_guncelle(
                self._edit_id, mevcut[3], yeni_deger, mevcut[5] or "", mevcut[6]
            )
        elif self._edit_col == 3:  # Açıklama
            self.db.planlanan_guncelle(
                self._edit_id, mevcut[3], mevcut[4], yeni_deger, mevcut[6]
            )
        elif self._edit_col == 4:  # Tutar
            # Naif float(replace(",", ".")) kullanmak "1.500" girişini 1.5'e
            # çeviriyordu (1000x hata) ve formatlanmış "1.234,56" değerini
            # sessizce yutuyordu. Uygulamanın geri kalanıyla aynı ayrıştırıcı.
            try:
                tutar = para_parse(yeni_deger)
            except ValueError:
                messagebox.showwarning(
                    "Geçersiz tutar",
                    f"'{yeni_deger}' bir tutar olarak okunamadı.\n"
                    "Değişiklik kaydedilmedi.",
                )
                self._planlama_yenile()
                return
            self.db.planlanan_guncelle(
                self._edit_id, mevcut[3], mevcut[4], mevcut[5] or "", tutar
            )

        self._planlama_yenile()

    def _plani_aktar(self):
        """Plandaki gelir/giderleri gerçek işlemlere aktar."""
        try:
            ay = int(self.p_ay.get())
            yil = int(self.p_yil.get())
        except ValueError:
            return

        plan = self.db.planlanan_listele(ay, yil)
        if not plan:
            messagebox.showwarning("Uyarı", "Bu ay için plan bulunamadı.")
            return

        if not messagebox.askyesno(
            "Aktar",
            f"{len(plan)} planlı işlem gerçek işlemlere aktarılsın mı?\n"
            "Tarih olarak ayın 1'i kullanılacak.\n"
            "(Daha önce aktarılmış kalemler tekrar aktarılmaz.)",
        ):
            return

        tarih = f"01.{ay:02d}.{yil}"
        try:
            sonuc = self.db.plani_aktar(ay, yil, tarih)
        except Exception as e:
            messagebox.showerror(
                "Hata", f"Aktarım sırasında bir sorun oluştu:\n{e}"
            )
            return

        mesaj = f"{sonuc['aktarilan']} işlem aktarıldı."
        if sonuc["atlanan"]:
            mesaj += (
                f"\n{sonuc['atlanan']} kalem daha önce aktarıldığı için atlandı."
            )
        messagebox.showinfo("Başarılı", mesaj)
        self._planlama_yenile()
        if self.dashboard_callback:
            self.dashboard_callback()

    def _kopyala(self):
        """Önceki ayın planını bu aya kopyala."""
        try:
            ay = int(self.p_ay.get())
            yil = int(self.p_yil.get())
        except ValueError:
            return

        # Önceki ayı hesapla
        if ay == 1:
            onceki_ay, onceki_yil = 12, yil - 1
        else:
            onceki_ay, onceki_yil = ay - 1, yil

        onceki = self.db.planlanan_listele(onceki_ay, onceki_yil)
        if not onceki:
            messagebox.showwarning(
                "Uyarı", f"{onceki_ay:02d}.{onceki_yil} için plan bulunamadı."
            )
            return

        mevcut = self.db.planlanan_listele(ay, yil)
        if mevcut:
            if not messagebox.askyesno(
                "Uyarı", "Bu ay için zaten plan var. Üzerine yazılsın mı?"
            ):
                return
            for m in mevcut:
                self.db.planlanan_sil(m[0])

        eklenen = 0
        for satir in onceki:
            self.db.planlanan_ekle(
                ay, yil, satir[3], satir[4], satir[5] or "", satir[6]
            )
            eklenen += 1

        messagebox.showinfo(
            "Başarılı", f"{eklenen} plan kalemi {ay:02d}.{yil} ayına kopyalandı."
        )
        self._planlama_yenile()

    # =========================================
    # BORÇLAR & ALACAKLAR SEKMESİ
    # =========================================

    def _borc_alacak_olustur(self):
        tab = self.tabview.tab("💳 Borçlar & Alacaklar")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Buton bar
        btn_bar = ctk.CTkFrame(tab, fg_color="transparent")
        btn_bar.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        ctk.CTkButton(
            btn_bar,
            text="➕ Yeni Borç/Alacak",
            width=160,
            height=32,
            fg_color="#0d9488",
            command=self._borc_ekle_ac,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_bar,
            text="💵 Ödeme Yap",
            width=110,
            height=32,
            fg_color="#16a34a",
            command=self._borc_odeme,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_bar,
            text="✏ Düzenle",
            width=100,
            height=32,
            fg_color="#f59e0b",
            command=self._borc_duzenle,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_bar,
            text="🗑 Sil",
            width=80,
            height=32,
            fg_color="#c0392b",
            command=self._borc_sil,
        ).pack(side="left")

        # Özet
        self.b_ozet = ctk.CTkLabel(
            btn_bar, text="", font=("Segoe UI", 14, "bold"), text_color="#5eead4"
        )
        self.b_ozet.pack(side="right")

        # Filtre
        ctk.CTkLabel(btn_bar, text="Durum:", font=("Segoe UI", 12)).pack(
            side="right", padx=(0, 5)
        )
        self.b_durum = ctk.CTkComboBox(
            btn_bar,
            width=110,
            values=["Aktif", "Ödendi", "Tümü"],
            command=lambda _: self._borclari_yenile(),
        )
        self.b_durum.set("Aktif")
        self.b_durum.pack(side="right", padx=(0, 15))

        # Ayraç
        ctk.CTkFrame(tab, height=1, fg_color="#334155").grid(
            row=1, column=0, sticky="ew", padx=15, pady=(5, 0)
        )

        # Tablo
        self.b_kolonlar = (
            "ID",
            "Tür",
            "Açıklama",
            "Kişi/Kurum",
            "Toplam",
            "Kalan",
            "Başlangıç",
            "Vade",
            "Durum",
        )
        self.b_tablo = ttk.Treeview(
            tab, columns=self.b_kolonlar, show="headings", height=10
        )
        self.b_tablo.grid(row=2, column=0, sticky="nsew", padx=15, pady=(5, 15))

        genislikler = [40, 70, 160, 120, 90, 90, 90, 90, 70]
        for k, w in zip(self.b_kolonlar, genislikler):
            self.b_tablo.heading(k, text=k)
            self.b_tablo.column(k, width=w, anchor="center")

        self._borclari_yenile()

    def _borclari_yenile(self):
        for item in self.b_tablo.get_children():
            self.b_tablo.delete(item)

        durum = self.b_durum.get()
        borclar = self.db.borclari_listele(durum)

        toplam_borc = 0.0
        toplam_alacak = 0.0
        for b in borclar:
            self.b_tablo.insert(
                "",
                "end",
                values=(
                    b["id"],
                    b["tur"],
                    b["aciklama"],
                    b["kisi"] or "",
                    para_formatla(b['toplam_tutar']),
                    para_formatla(b['kalan_tutar']),
                    b["baslangic_tarih"] or "",
                    b["vade_tarih"] or "",
                    b["durum"],
                ),
            )
            if b["durum"] == "Aktif":
                if b["tur"] == "Borç":
                    toplam_borc += b["kalan_tutar"]
                else:
                    toplam_alacak += b["kalan_tutar"]

        self.b_ozet.configure(
            text=f"🔴 Borç: {para_formatla(toplam_borc, ondalik=0)}  |  "
            f"🟢 Alacak: {para_formatla(toplam_alacak, ondalik=0)}  |  "
            f"📊 Net: {para_formatla(toplam_alacak - toplam_borc, ondalik=0)}"
        )

    def _borc_ekle_ac(self):
        BorcPenceresi(self, "Yeni Borç/Alacak", self._borc_kaydet)

    def _borc_kaydet(self, pencere, data):
        self.db.borc_ekle(**data)
        pencere.destroy()
        self._borclari_yenile()

    def _borc_odeme(self):
        secili = self.b_tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Ödeme için bir satır seçin.")
            return
        veri = self.b_tablo.item(secili[0])["values"]
        BorcOdemePenceresi(
            self, int(veri[0]), self.db, self._borc_odeme_sonrasi
        )

    def _borc_odeme_sonrasi(self):
        self._borclari_yenile()
        if self.dashboard_callback:
            self.dashboard_callback()

    def _borc_duzenle(self):
        secili = self.b_tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Düzenlemek için bir satır seçin.")
            return
        veri = self.b_tablo.item(secili[0])["values"]
        BorcDuzenlePenceresi(
            self, "Borç/Alacak Düzenle", int(veri[0]), self.db, self._borclari_yenile
        )

    def _borc_sil(self):
        secili = self.b_tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Silmek için bir satır seçin.")
            return
        veri = self.b_tablo.item(secili[0])["values"]
        if messagebox.askyesno("Sil", "Bu kayıt silinsin mi?"):
            self.db.borc_sil(int(veri[0]))
            self._borclari_yenile()

    # =========================================
    # TEKRARLAYAN İŞLEMLER SEKMESİ
    # =========================================

    def _tekrarlayan_olustur(self):
        tab = self.tabview.tab("🔄 Tekrarlayan")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            tab,
            text="Her ay belirtilen günde otomatik eklenir",
            font=("Segoe UI", 12),
            text_color="#94a3b8",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        # Ekleme formu
        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=15, pady=5)

        self.t_tur = ctk.CTkComboBox(form, width=90, values=["Gelir", "Gider"])
        self.t_tur.set("Gider")
        self.t_tur.pack(side="left", padx=3)

        self.t_kategori = ctk.CTkEntry(form, width=100, placeholder_text="Kategori")
        self.t_kategori.pack(side="left", padx=3)

        self.t_aciklama = ctk.CTkEntry(form, width=140, placeholder_text="Açıklama")
        self.t_aciklama.pack(side="left", padx=3)

        self.t_tutar = ctk.CTkEntry(form, width=90, placeholder_text="Tutar")
        tutar_bind(self.t_tutar)
        self.t_tutar.pack(side="left", padx=3)

        ctk.CTkLabel(form, text="Gün:", font=("Segoe UI", 12)).pack(side="left", padx=(5, 2))
        self.t_gun = ctk.CTkEntry(form, width=45, placeholder_text="1")
        self.t_gun.insert(0, "1")
        self.t_gun.pack(side="left", padx=3)

        ctk.CTkButton(
            form, text="➕ Ekle", width=70, height=32,
            fg_color="#0d9488", command=self._tekrarlayan_ekle,
        ).pack(side="left", padx=5)

        # Liste
        self.t_liste = ttk.Treeview(
            tab, columns=("ID", "Tur", "Kategori", "Açıklama", "Tutar", "Gün", "Aktif"),
            show="headings", height=8,
        )
        for k in ("ID", "Tur", "Kategori", "Açıklama", "Tutar", "Gün", "Aktif"):
            self.t_liste.heading(k, text=k)
            self.t_liste.column(k, width=80, anchor="center")
        self.t_liste.grid(row=2, column=0, sticky="nsew", padx=15, pady=10)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 10))
        ctk.CTkButton(
            btn_row, text="🔄 Aktif/Deaktif", width=120, height=28,
            fg_color="#f59e0b", command=self._tekrarlayan_toggle,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_row, text="🗑 Sil", width=70, height=28,
            fg_color="#c0392b", command=self._tekrarlayan_sil,
        ).pack(side="left", padx=3)

        self._tekrarlayan_yenile()

    def _tekrarlayan_yenile(self):
        self.t_liste.delete(*self.t_liste.get_children())
        for t in self.db.tekrarlayan_listele():
            self.t_liste.insert("", "end", values=(
                t["id"], t["tur"], t["kategori"], t["aciklama"],
                para_formatla(t['tutar'], sembol=False), t["gun"],
                "✅" if t["aktif"] else "❌"
            ))

    def _tekrarlayan_ekle(self):
        try:
            tur = self.t_tur.get()
            kat = self.t_kategori.get().strip()
            ack = self.t_aciklama.get().strip()
            tut = tutar_oku(self.t_tutar)
            gun = int(self.t_gun.get())
            if not kat or tut <= 0:
                raise ValueError
            if gun < 1 or gun > 31:
                messagebox.showwarning("Uyarı", "Gün 1-31 arası olmalı.")
                return
        except (ValueError, AttributeError):
            messagebox.showerror("Hata", "Tüm alanları doğru doldurun.")
            return
        self.db.tekrarlayan_ekle(tur, kat, ack, tut, gun)
        self._tekrarlayan_yenile()

    def _tekrarlayan_toggle(self):
        secili = self.t_liste.selection()
        if not secili:
            return
        id_ = self.t_liste.item(secili[0])["values"][0]
        self.db.tekrarlayan_toggle(id_)
        self._tekrarlayan_yenile()

    def _tekrarlayan_sil(self):
        secili = self.t_liste.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Silmek için bir satır seçin.")
            return
        # Diğer silme işlemleriyle tutarlı onay (önceden onaysız siliyordu)
        if not messagebox.askyesno(
            "Sil", "Bu tekrarlayan işlem kuralı silinsin mi?"
        ):
            return
        id_ = self.t_liste.item(secili[0])["values"][0]
        self.db.tekrarlayan_sil(id_)
        self._tekrarlayan_yenile()

    # =========================================
    # TASARRUF HEDEFLERİ SEKMESİ
    # =========================================

    def _tasarruf_olustur(self):
        tab = self.tabview.tab("🎯 Tasarruf Hedefleri")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            tab, text="Hedef tutar ve tarih belirleyip birikimini takip et",
            font=("Segoe UI", 12), text_color="#94a3b8",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=15, pady=5)

        self.h_ad = ctk.CTkEntry(form, width=180, placeholder_text="Hedef adı (örn: Tatil)")
        self.h_ad.pack(side="left", padx=3)

        self.h_tutar = ctk.CTkEntry(form, width=110, placeholder_text="Hedef Tutar")
        tutar_bind(self.h_tutar)
        self.h_tutar.pack(side="left", padx=3)

        self.h_tarih = ctk.CTkEntry(form, width=110, placeholder_text="GG.AA.YYYY (ops.)")
        tarih_bind(self.h_tarih)
        self.h_tarih.pack(side="left", padx=3)

        ctk.CTkButton(
            form, text="🎯 Hedef Ekle", width=110, height=32,
            fg_color="#9333ea", command=self._tasarruf_ekle,
        ).pack(side="left", padx=5)

        self.h_liste_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.h_liste_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(5, 15))
        self.h_liste_frame.grid_columnconfigure(0, weight=1)

        self._tasarruf_yenile()

    def _tasarruf_ekle(self):
        ad = self.h_ad.get().strip()
        try:
            tutar = tutar_oku(self.h_tutar)
            if not ad or tutar <= 0:
                raise ValueError
        except (ValueError, AttributeError):
            messagebox.showerror("Hata", "Hedef adı ve geçerli bir tutar girin.")
            return
        tarih = self.h_tarih.get().strip()
        try:
            self.db.tasarruf_hedefi_ekle(ad, tutar, tarih)
        except Exception as e:
            messagebox.showerror("Hata", f"Geçersiz tarih: {e}")
            return
        self.h_ad.delete(0, "end")
        self.h_tutar.delete(0, "end")
        self.h_tarih.delete(0, "end")
        self._tasarruf_yenile()

    def _tasarruf_yenile(self):
        for widget in self.h_liste_frame.winfo_children():
            widget.destroy()

        hedefler = self.db.tasarruf_hedefleri_listele()
        if not hedefler:
            ctk.CTkLabel(
                self.h_liste_frame, text="Henüz tasarruf hedefi eklenmedi.",
                font=("Segoe UI", 12), text_color="#94a3b8",
            ).pack(pady=20)
            return

        for h in hedefler:
            oran = (
                min(h["biriken_tutar"] / h["hedef_tutar"] * 100, 100)
                if h["hedef_tutar"] > 0 else 0
            )
            renk = "#22c55e" if oran >= 90 else "#f59e0b" if oran >= 50 else "#ef4444"

            kart = ctk.CTkFrame(self.h_liste_frame, corner_radius=12, fg_color=tema.PANEL)
            kart.pack(fill="x", pady=6)

            ust = ctk.CTkFrame(kart, fg_color="transparent")
            ust.pack(fill="x", padx=12, pady=(10, 2))
            baslik = h["ad"]
            if h["hedef_tarih"]:
                try:
                    dt = datetime.strptime(h["hedef_tarih"], "%Y-%m-%d")
                    baslik += f"  ·  🗓 {dt.strftime('%d.%m.%Y')}"
                except ValueError:
                    pass
            ctk.CTkLabel(ust, text=baslik, font=("Segoe UI", 14, "bold")).pack(side="left")
            ctk.CTkLabel(
                ust, text=f"%{int(oran)}", font=("Segoe UI", 13, "bold"), text_color=renk,
            ).pack(side="right")

            bar_bg = ctk.CTkFrame(kart, height=16, fg_color="#1e293b", corner_radius=8)
            bar_bg.pack(fill="x", padx=12, pady=4)
            bar_fill = ctk.CTkFrame(bar_bg, height=16, fg_color=renk, corner_radius=8)
            bar_fill.place(relx=0, rely=0, relheight=1, relwidth=min(oran / 100, 1))

            alt = ctk.CTkFrame(kart, fg_color="transparent")
            alt.pack(fill="x", padx=12, pady=(2, 10))
            ctk.CTkLabel(
                alt,
                text=f"{para_formatla(h['biriken_tutar'], sembol=False)} / "
                f"{para_formatla(h['hedef_tutar'])}",
                font=("Segoe UI", 11), text_color="#94a3b8",
            ).pack(side="left")

            btn_frame = ctk.CTkFrame(alt, fg_color="transparent")
            btn_frame.pack(side="right")
            ctk.CTkButton(
                btn_frame, text="+ Katkı", width=70, height=26,
                fg_color="#0d9488", command=lambda h=h: self._tasarruf_katki_penceresi(h),
            ).pack(side="left", padx=3)
            ctk.CTkButton(
                btn_frame, text="🗑", width=32, height=26,
                fg_color="#c0392b", command=lambda h=h: self._tasarruf_sil(h["id"]),
            ).pack(side="left", padx=3)

    def _tasarruf_katki_penceresi(self, hedef):
        pencere = ctk.CTkToplevel(self)
        pencere.title("Katkı Ekle")
        pencere.geometry("300x180")
        modal_yap(pencere, self)

        ctk.CTkLabel(
            pencere, text=f"🎯 {hedef['ad']}", font=("Segoe UI", 16, "bold")
        ).pack(pady=(16, 8))
        tutar_entry = ctk.CTkEntry(pencere, width=200, placeholder_text="Tutar (₺)")
        tutar_bind(tutar_entry)
        tutar_entry.pack(pady=8)

        def kaydet():
            try:
                tutar = tutar_oku(tutar_entry)
            except ValueError:
                messagebox.showerror("Hata", "Geçerli bir tutar girin.")
                return
            try:
                self.db.tasarruf_katki_ekle(hedef["id"], tutar)
            except Exception as e:
                messagebox.showerror("Hata", f"Katkı eklenemedi:\n{e}")
                return
            pencere.destroy()
            self._tasarruf_yenile()
            if self.dashboard_callback:
                self.dashboard_callback()

        ctk.CTkButton(pencere, text="💾 Ekle", width=180, command=kaydet).pack(pady=12)

    def _tasarruf_sil(self, id_):
        if not messagebox.askyesno("Sil", "Bu hedef silinsin mi?"):
            return
        self.db.tasarruf_hedefi_sil(id_)
        self._tasarruf_yenile()


# =========================================
# YARDIMCI PENCERELER
# =========================================


class Pencere(ctk.CTkToplevel):
    """Plan ekleme penceresi."""

    def __init__(self, parent, baslik, kaydet_cb, extra=None):
        super().__init__(parent)
        self.title(baslik)
        self.geometry("400x340")
        self.resizable(False, False)
        self._kaydet_cb = kaydet_cb
        self._extra = extra or {}

        # Modal: arkaya kaçmaz, ana sayfaya tıklanamaz
        modal_yap(self, parent)

        ctk.CTkLabel(self, text=baslik, font=("Segoe UI", 20, "bold")).pack(pady=16)

        self.kategori = ctk.CTkEntry(self, width=300, placeholder_text="Kategori")
        self.kategori.pack(pady=8)

        self.tur = ctk.CTkComboBox(self, width=300, values=["Gelir", "Gider"])
        self.tur.set("Gider")
        self.tur.pack(pady=8)

        self.aciklama = ctk.CTkEntry(self, width=300, placeholder_text="Açıklama")
        self.aciklama.pack(pady=8)

        self.tutar = ctk.CTkEntry(self, width=300, placeholder_text="Tutar (₺)")
        self.tutar.pack(pady=8)
        tutar_bind(self.tutar)

        ctk.CTkButton(self, text="💾 Kaydet", width=200, command=self._kaydet).pack(
            pady=16
        )

    def _kaydet(self):
        try:
            tutar = tutar_oku(self.tutar)
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir tutar giriniz.")
            return
        data = {
            **self._extra,
            "kategori": self.kategori.get(),
            "tur": self.tur.get(),
            "aciklama": self.aciklama.get(),
            "tutar": tutar,
        }
        self._kaydet_cb(self, data)


class BorcPenceresi(ctk.CTkToplevel):
    """Borç/Alacak ekleme penceresi."""

    def __init__(self, parent, baslik, kaydet_cb):
        super().__init__(parent)
        self.title(baslik)
        self.geometry("420x460")
        self.resizable(False, False)
        self._kaydet_cb = kaydet_cb

        # Modal: arkaya kaçmaz, ana sayfaya tıklanamaz
        modal_yap(self, parent)

        ctk.CTkLabel(self, text=baslik, font=("Segoe UI", 20, "bold")).pack(pady=16)

        self.tur = ctk.CTkComboBox(self, width=300, values=["Borç", "Alacak"])
        self.tur.set("Borç")
        self.tur.pack(pady=8)

        self.aciklama = ctk.CTkEntry(
            self, width=300, placeholder_text="Açıklama (örn: Kredi Kartı)"
        )
        self.aciklama.pack(pady=8)

        self.kisi = ctk.CTkEntry(self, width=300, placeholder_text="Kişi / Kurum")
        self.kisi.pack(pady=8)

        self.toplam = ctk.CTkEntry(self, width=300, placeholder_text="Toplam Tutar (₺)")
        self.toplam.pack(pady=8)
        tutar_bind(self.toplam)

        self.kalan = ctk.CTkEntry(self, width=300, placeholder_text="Kalan Tutar (₺)")
        self.kalan.pack(pady=8)
        tutar_bind(self.kalan)

        self.baslangic = ctk.CTkEntry(
            self, width=300, placeholder_text="Başlangıç Tarihi (GG.AA.YYYY)"
        )
        self.baslangic.pack(pady=8)
        tarih_bind(self.baslangic)

        self.vade = ctk.CTkEntry(
            self, width=300, placeholder_text="Vade Tarihi (GG.AA.YYYY)"
        )
        self.vade.pack(pady=8)
        tarih_bind(self.vade)

        ctk.CTkButton(self, text="💾 Kaydet", width=200, command=self._kaydet).pack(
            pady=16
        )

    def _kaydet(self):
        try:
            toplam = tutar_oku(self.toplam)
            kalan = tutar_oku(self.kalan)
        except ValueError:
            messagebox.showerror("Hata", "Geçerli tutar giriniz.")
            return
        data = {
            "tur": self.tur.get(),
            "aciklama": self.aciklama.get(),
            "kisi": self.kisi.get(),
            "toplam": toplam,
            "kalan": kalan,
            "baslangic": self.baslangic.get(),
            "vade": self.vade.get(),
        }
        self._kaydet_cb(self, data)


class BorcOdemePenceresi(ctk.CTkToplevel):
    """Borç/Alacak ödeme penceresi — kalanı düşürür ve gerçek işlem üretir."""

    def __init__(self, parent, borc_id, db, yenile_cb):
        super().__init__(parent)
        self.db = db
        self.borc_id = borc_id
        self._yenile_cb = yenile_cb
        self.title("Ödeme Yap")
        self.geometry("380x340")
        self.resizable(False, False)

        modal_yap(self, parent)

        borclar = db.borclari_listele("Aktif") + db.borclari_listele("Ödendi")
        mevcut = next((b for b in borclar if b["id"] == borc_id), None)
        if not mevcut:
            messagebox.showerror("Hata", "Kayıt bulunamadı.")
            self.destroy()
            return
        self._mevcut = mevcut

        ctk.CTkLabel(
            self, text="💵 Ödeme Yap", font=("Segoe UI", 20, "bold")
        ).pack(pady=(16, 4))
        ctk.CTkLabel(
            self, text=f"📌 {mevcut['aciklama']}", font=("Segoe UI", 13)
        ).pack()
        ctk.CTkLabel(
            self,
            text=f"Kalan: {para_formatla(mevcut['kalan_tutar'])}",
            font=("Segoe UI", 12), text_color="#94a3b8",
        ).pack(pady=(0, 8))

        self.tutar = ctk.CTkEntry(self, width=300, placeholder_text="Ödeme Tutarı (₺)")
        self.tutar.pack(pady=8)
        tutar_bind(self.tutar)

        self.tarih = ctk.CTkEntry(self, width=300, placeholder_text="Tarih (GG.AA.YYYY)")
        self.tarih.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.tarih.pack(pady=8)
        tarih_bind(self.tarih)

        self.islem_olustur = ctk.CTkCheckBox(
            self, text="Gelir/gider işlemi olarak da kaydet"
        )
        self.islem_olustur.select()
        self.islem_olustur.pack(pady=(8, 0))

        # Ne yaptığını açıkça söyle: kutu varsayılan işaretli olduğu için,
        # harcamayı ayrıca kaydeden kullanıcıda habersiz mükerrer gider
        # oluşuyor ve toplam gider şişiyordu.
        ctk.CTkLabel(
            self,
            text="Bu ödemeyi ayrıca harcama listene ekler",
            font=("Segoe UI", 11),
            text_color="#94a3b8",
        ).pack(pady=(0, 8))

        ctk.CTkButton(
            self, text="💾 Ödemeyi Kaydet", width=220, fg_color="#16a34a",
            command=self._kaydet,
        ).pack(pady=12)

    def _kaydet(self):
        try:
            tutar = tutar_oku(self.tutar)
            if tutar <= 0:
                messagebox.showwarning("Uyarı", "Ödeme tutarı sıfırdan büyük olmalı.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir tutar girin.")
            return
        try:
            self.db.borc_odeme_yap(
                self.borc_id, tutar, self.tarih.get(),
                islem_olustur=bool(self.islem_olustur.get()),
            )
        except Exception as e:
            messagebox.showerror("Hata", f"Ödeme kaydedilemedi:\n{e}")
            return
        self.destroy()
        self._yenile_cb()


class BorcDuzenlePenceresi(ctk.CTkToplevel):
    """Borç/Alacak düzenleme penceresi."""

    def __init__(self, parent, baslik, borc_id, db, yenile_cb):
        super().__init__(parent)
        self.title(baslik)
        self.geometry("400x280")
        self.resizable(False, False)
        self.db = db
        self.borc_id = borc_id
        self._yenile_cb = yenile_cb

        # Modal: arkaya kaçmaz, ana sayfaya tıklanamaz
        modal_yap(self, parent)

        # Mevcut değerleri bul
        borclar = db.borclari_listele("Aktif") + db.borclari_listele("Ödendi")
        mevcut = None
        for b in borclar:
            if b["id"] == borc_id:
                mevcut = b
                break
        if not mevcut:
            messagebox.showerror("Hata", "Kayıt bulunamadı.")
            self.destroy()
            return

        ctk.CTkLabel(self, text=baslik, font=("Segoe UI", 20, "bold")).pack(pady=16)

        ctk.CTkLabel(self, text=f"📌 {mevcut['aciklama']}").pack()

        self.kalan = ctk.CTkEntry(self, width=300, placeholder_text="Kalan Tutar")
        # str(float) yazmak ("1500.0") tutar_oku'nun noktayı binlik ayraç
        # sanmasına ve kalanın 10x-100x şişmesine yol açıyordu — alan,
        # okunduğu formatla aynı (Türk) formatta doldurulmalı.
        self.kalan.insert(0, para_formatla(mevcut["kalan_tutar"], sembol=False))
        self.kalan.pack(pady=8)
        tutar_bind(self.kalan)

        self.durum = ctk.CTkComboBox(self, width=300, values=["Aktif", "Ödendi"])
        self.durum.set(mevcut["durum"])
        self.durum.pack(pady=8)

        ctk.CTkButton(self, text="💾 Güncelle", width=200, command=self._guncelle).pack(
            pady=16
        )

    def _guncelle(self):
        try:
            kalan = tutar_oku(self.kalan)
        except ValueError:
            messagebox.showerror("Hata", "Geçerli tutar giriniz.")
            return
        self.db.borc_guncelle(self.borc_id, kalan, self.durum.get())
        self.destroy()
        self._yenile_cb()
