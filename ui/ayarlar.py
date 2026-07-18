from tkinter import filedialog, messagebox
from typing import Any, Callable, Optional

import customtkinter as ctk  # type: ignore

from ui import tema
from ui.utils import modal_yap


class AyarlarSayfasi(ctk.CTkFrame):
    def __init__(
        self,
        parent: Any,
        db: Any,
        dashboard_callback: Optional[Callable[[], None]] = None,
        hesap_degistir_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent, fg_color="transparent")  # type: ignore
        self.db = db
        self.dashboard_callback = dashboard_callback
        self.hesap_degistir_callback = hesap_degistir_callback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Ana kart
        kart = ctk.CTkFrame(
            self,
            corner_radius=20,
            fg_color=tema.KART,
            border_width=1,
            border_color="#14b8a6",
        )
        kart.pack(pady=30, padx=60, fill="both", expand=True)

        ctk.CTkLabel(
            kart,
            text="⚙️  Ayarlar",
            font=("Segoe UI", 30, "bold"),
            text_color="#5eead4",
        ).pack(pady=(30, 5))

        # Kullanıcı bilgisi
        kullanici_adi = self.db.ayar_oku("aktif_kullanici_adi", "Bilinmiyor")
        ctk.CTkLabel(
            kart,
            text=f"👤  {kullanici_adi}",
            font=("Segoe UI", 16, "bold"),
            text_color="#2dd4bf",
        ).pack(pady=(0, 20))

        # Ayraç
        ctk.CTkFrame(kart, height=1, fg_color="#334155").pack(
            fill="x", padx=40, pady=(0, 15)
        )

        ctk.CTkButton(
            kart, text="🗂 Yedek Oluştur", width=220, command=self.yedek_olustur
        ).pack(
            pady=8
        )  # type: ignore
        ctk.CTkButton(
            kart, text="♻️ Yedeği Geri Yükle", width=220, command=self.yedek_geri_yukle
        ).pack(
            pady=8
        )  # type: ignore

        # Ayraç
        ctk.CTkFrame(kart, height=1, fg_color="#334155").pack(
            fill="x", padx=40, pady=15
        )

        ctk.CTkLabel(
            kart,
            text="Hesap İşlemleri",
            font=("Segoe UI", 14, "bold"),
            text_color="#94a3b8",
        ).pack()

        ctk.CTkButton(
            kart,
            text="👤 Profil Düzenle",
            width=220,
            fg_color="#0ea5e9",
            command=self._profil_duzenle,
        ).pack(
            pady=6
        )  # type: ignore

        ctk.CTkButton(
            kart,
            text="🔒 Şifre Değiştir",
            width=220,
            fg_color="#6366f1",
            command=self._sifre_degistir,
        ).pack(
            pady=6
        )  # type: ignore

        ctk.CTkButton(
            kart,
            text="🔄 Hesap Değiştir",
            width=220,
            fg_color="#f59e0b",
            hover_color="#d97706",
            command=self._hesap_degistir,
        ).pack(
            pady=6
        )  # type: ignore

        # Ayraç
        ctk.CTkFrame(kart, height=1, fg_color="#334155").pack(
            fill="x", padx=40, pady=10
        )

        ctk.CTkLabel(
            kart, text="Sistem", font=("Segoe UI", 14, "bold"), text_color="#94a3b8"
        ).pack()

        ctk.CTkButton(
            kart,
            text="🔔 Bildirim Testi",
            width=220,
            fg_color="#0ea5e9",
            command=self._bildirim_test,
        ).pack(
            pady=6
        )  # type: ignore

        # --- Admin Paneli (sadece admin görebilir) ---
        # Yetki kararı paylaşılan ayarlar tablosu yerine veri katmanındaki
        # aktif oturum kimliğinden verilir.
        if self.db.aktif_admin_mi():
            ctk.CTkFrame(kart, height=1, fg_color="#f59e0b").pack(
                fill="x", padx=40, pady=10
            )

            ctk.CTkLabel(
                kart,
                text="👑 Admin — Kullanıcı Yönetimi",
                font=("Segoe UI", 14, "bold"),
                text_color="#fbbf24",
            ).pack(pady=(5, 10))

            self._admin_kart = kart
            self._admin_liste_frame = None
            self._admin_kullanici_listesi(kart)

    def _admin_listesini_yenile(self):
        """Admin kullanıcı listesini yalnızca kendi frame'ini yeniden kurarak
        yeniler (tüm sayfayı destroy+__init__ etmeden)."""
        if getattr(self, "_admin_liste_frame", None) is not None:
            try:
                self._admin_liste_frame.destroy()
            except Exception:
                pass
        self._admin_kullanici_listesi(self._admin_kart)

    def _admin_kullanici_listesi(self, kart):
        """Admin için kullanıcı listesini göster."""
        kullanicilar = self.db.kullanici_listele()

        liste_frame = ctk.CTkScrollableFrame(kart, height=160, fg_color=tema.PANEL)
        liste_frame.pack(fill="x", padx=40, pady=(0, 8))
        self._admin_liste_frame = liste_frame

        for k in kullanicilar:
            row = ctk.CTkFrame(liste_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            admin_badge = " 👑" if k["id"] == 1 else ""
            ctk.CTkLabel(
                row,
                text=f'{k["kullanici_adi"]}{admin_badge} — {k["ad_soyad"]}',
                font=("Segoe UI", 12),
                text_color="#cbd5e1",
            ).pack(side="left", padx=(5, 10))

            if k["id"] != 1:  # Admin kendini silemez
                ctk.CTkButton(
                    row,
                    text="🔑 Şifre Sıfırla",
                    width=100,
                    height=28,
                    font=("Segoe UI", 11),
                    fg_color="#6366f1",
                    command=lambda kid=k["id"]: self._admin_sifre_sifirla(kid),
                ).pack(side="right", padx=2)
                ctk.CTkButton(
                    row,
                    text="🗑️ Sil",
                    width=60,
                    height=28,
                    font=("Segoe UI", 11),
                    fg_color="#c0392b",
                    command=lambda kid=k["id"], kad=k[
                        "kullanici_adi"
                    ]: self._admin_kullanici_sil(kid, kad),
                ).pack(side="right", padx=2)

    def _admin_sifre_sifirla(self, kullanici_id):
        from tkinter import simpledialog

        yeni = simpledialog.askstring(
            "Şifre Sıfırla", "Yeni şifreyi girin (en az 8 karakter):",
            parent=self, show="•",
        )
        if not yeni:
            return
        try:
            self.db.kullanici_sifre_degistir(kullanici_id, yeni)
            messagebox.showinfo("Başarılı", "Kullanıcının şifresi sıfırlandı.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _admin_kullanici_sil(self, kullanici_id, kullanici_adi):
        if messagebox.askyesno(
            "Kullanıcıyı Sil",
            f"'{kullanici_adi}' kullanıcısını silmek istediğinize emin misiniz?\n\nBu işlem geri alınamaz!",
        ):
            try:
                silindi = self.db.kullanici_sil(kullanici_id)
            except Exception as e:
                messagebox.showerror("Hata", str(e))
                return
            if silindi:
                messagebox.showinfo("Başarılı", f"'{kullanici_adi}' silindi.")
                # Sadece admin liste bölümünü yeniden kur (destroy+__init__
                # yerine — bu, yok edilmiş widget üzerinde __init__ çağırmanın
                # yol açtığı callback sızıntısı/tanımsız davranışı önler)
                self._admin_listesini_yenile()
            else:
                messagebox.showerror("Hata", "Admin kullanıcısı silinemez!")

    def _bildirim_test(self):
        try:
            from plyer import notification

            notification.notify(
                title="🧪 Fineding — Test Bildirimi",
                message="Bildirim sistemi çalışıyor!\nBorç vadesi yaklaştığında böyle uyarı alacaksın.",
                app_name="Fineding",
                timeout=8,
            )
            messagebox.showinfo(
                "Başarılı", "Bildirim gönderildi!\nSağ alt köşeyi kontrol et."
            )
        except Exception as e:
            msg = (
                f"Bildirim gönderilemedi:\n{e}\n\n"
                "Windows Ayarlar > Sistem > Bildirimler "
                "kısmından Python bildirimlerini kontrol et."
            )
            messagebox.showerror("Hata", msg)

    def _sifre_degistir(self):
        SifreDegistirPenceresi(self, self.db)

    def _profil_duzenle(self):
        ProfilDuzenlePenceresi(self, self.db)

    def _hesap_degistir(self):
        if messagebox.askyesno(
            "Hesap Değiştir", "Oturum kapatılıp giriş ekranına dönülecek. Emin misiniz?"
        ):
            if self.hesap_degistir_callback:
                self.hesap_degistir_callback()

    def yedek_olustur(self):
        yol = filedialog.asksaveasfilename(
            defaultextension=".db", filetypes=[("Veritabanı", "*.db")]
        )
        if yol:
            self.db.yedekle(yol)
            messagebox.showinfo("Başarılı", f"Yedek oluşturuldu: {yol}")

    def yedek_geri_yukle(self):
        yol = filedialog.askopenfilename(
            defaultextension=".db", filetypes=[("Veritabanı", "*.db")]
        )
        if yol:
            self.db.geri_yukle(yol)
            messagebox.showinfo("Başarılı", "Yedek geri yüklendi.")


class SifreDegistirPenceresi(ctk.CTkToplevel):
    """Şifre değiştirme penceresi."""

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("Şifre Değiştir")
        self.geometry("380x320")
        self.resizable(False, False)

        # Modal: arkaya kaçmaz, ana sayfaya tıklanamaz
        modal_yap(self, parent)

        ctk.CTkLabel(
            self, text="🔒 Şifre Değiştir", font=("Segoe UI", 20, "bold")
        ).pack(pady=20)

        self.eski_sifre = ctk.CTkEntry(
            self,
            width=280,
            placeholder_text="Mevcut Şifre",
            font=("Segoe UI", 13),
            show="•",
        )
        self.eski_sifre.pack(pady=8)

        self.yeni_sifre = ctk.CTkEntry(
            self,
            width=280,
            placeholder_text="Yeni Şifre",
            font=("Segoe UI", 13),
            show="•",
        )
        self.yeni_sifre.pack(pady=8)

        self.yeni_tekrar = ctk.CTkEntry(
            self,
            width=280,
            placeholder_text="Yeni Şifre (Tekrar)",
            font=("Segoe UI", 13),
            show="•",
        )
        self.yeni_tekrar.pack(pady=8)

        ctk.CTkButton(
            self,
            text="💾 Şifreyi Güncelle",
            width=220,
            fg_color="#6366f1",
            command=self._guncelle,
        ).pack(pady=16)

    def _guncelle(self):
        eski = self.eski_sifre.get()
        yeni = self.yeni_sifre.get()
        yeni2 = self.yeni_tekrar.get()

        if not eski or not yeni:
            messagebox.showerror("Hata", "Tüm alanları doldurun.")
            return

        kullanici_adi = self.db.ayar_oku("aktif_kullanici_adi", "")
        if not self.db.kullanici_dogrula(kullanici_adi, eski):
            messagebox.showerror("Hata", "Mevcut şifre hatalı!")
            return
        if yeni != yeni2:
            messagebox.showerror("Hata", "Yeni şifreler eşleşmiyor!")
            return

        kullanici_id_str = self.db.ayar_oku("aktif_kullanici_id", "0")
        if not kullanici_id_str or kullanici_id_str == "0":
            messagebox.showerror("Hata", "Kullanıcı bilgisi bulunamadı.")
            self.destroy()
            return
        kullanici_id = int(kullanici_id_str)
        try:
            self.db.kullanici_sifre_degistir(kullanici_id, yeni)
        except Exception as e:
            # Şifre politikası (min uzunluk) veya yetki hatası
            messagebox.showerror("Hata", str(e))
            return
        messagebox.showinfo("Başarılı", "Şifre güncellendi!")
        self.destroy()


class ProfilDuzenlePenceresi(ctk.CTkToplevel):
    """Profil düzenleme penceresi."""

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("Profil Düzenle")
        self.geometry("380x260")
        self.resizable(False, False)

        modal_yap(self, parent)

        ctk.CTkLabel(
            self, text="👤 Profil Düzenle", font=("Segoe UI", 20, "bold")
        ).pack(pady=20)

        mevcut_ad = self.db.ayar_oku("aktif_kullanici_adi", "")
        ctk.CTkLabel(
            self,
            text=f"Kullanıcı: {mevcut_ad}",
            font=("Segoe UI", 12),
            text_color="#94a3b8",
        ).pack()

        # Mevcut adı veritabanından oku
        k_id = self.db.ayar_oku("aktif_kullanici_id", "0")
        mevcut_isim = (
            self.db.kullanici_ad_oku(int(k_id)) if k_id and k_id != "0" else ""
        )

        self.ad_soyad = ctk.CTkEntry(
            self, width=280, placeholder_text="👤 Ad Soyad", font=("Segoe UI", 13)
        )
        self.ad_soyad.insert(0, mevcut_isim)
        self.ad_soyad.pack(pady=12)

        ctk.CTkButton(
            self,
            text="💾 Kaydet",
            width=220,
            fg_color="#0ea5e9",
            command=self._guncelle,
        ).pack(pady=12)

    def _guncelle(self):
        yeni_ad = self.ad_soyad.get().strip()
        if not yeni_ad:
            messagebox.showerror("Hata", "Ad soyad boş olamaz.")
            return

        # Kimlik, paylaşılan 'ayarlar' tablosu yerine bellekteki oturumdan
        # okunur: ayarlar tablosu kullanıcıdan bağımsız (global) olduğu için
        # değeri bayat kalabiliyor ve yanlış profili güncelleyebiliyordu.
        kullanici_id = self.db.aktif_kullanici_id
        if not kullanici_id:
            messagebox.showerror("Hata", "Kullanıcı bilgisi bulunamadı.")
            self.destroy()
            return

        self.db.kullanici_profil_guncelle(kullanici_id, yeni_ad)
        messagebox.showinfo("Başarılı", f"Profil güncellendi: {yeni_ad}")
        self.destroy()
