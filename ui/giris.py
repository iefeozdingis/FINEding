"""Giriş ekranı — kullanıcı doğrulama ve kayıt."""

from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image


class GirisEkrani(ctk.CTk):
    """Uygulama başlangıcında gösterilen giriş/kayıt penceresi."""

    def __init__(self, db, on_login_success):
        super().__init__()
        self.db = db
        self.on_login_success = on_login_success
        self.kullanici = None

        self.title("Fineding — Giriş")
        self.geometry("480x580")
        self.resizable(False, False)

        # Ortala
        self.update_idletasks()
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        x = (w - 480) // 2
        y = (h - 580) // 2
        self.geometry(f"+{x}+{y}")

        # İkon
        from pathlib import Path

        icon_path = Path(__file__).parent.parent / "assets" / "app_icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self._arayuz_olustur()

        # İlk kullanıcı kontrolü
        kullanicilar = self.db.kullanici_listele()
        if not kullanicilar:
            self._hos_geldin_label = ctk.CTkLabel(
                self,
                text="🎉 Hoş geldin! Başlamak için\n📝 Yeni Hesap Oluştur'a tıkla.",
                font=("Segoe UI", 12),
                text_color="#5eead4",
                justify="center",
            )
            self._hos_geldin_label.pack(pady=(5, 0))

        # Beni hatırla kontrolü
        kayitli = self.db.ayar_oku("beni_hatirla_kullanici", "")
        if kayitli:
            self.kullanici_adi.insert(0, kayitli)
            self.beni_hatirla.select()
            self.sifre.focus()
        else:
            self.kullanici_adi.focus()

    def _arayuz_olustur(self):
        # Üst logo alanı - logomuzu göster
        logo_path = Path(__file__).parent.parent / "assets" / "app_icon.ico"
        if logo_path.exists():
            logo_img = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(70, 70),
            )
            ctk.CTkLabel(self, image=logo_img, text="").pack(pady=(30, 5))

        ctk.CTkLabel(
            self, text="FINEding", font=("Segoe UI", 24, "bold"), text_color="#5eead4"
        ).pack()

        ctk.CTkLabel(
            self,
            text="Finansal geleceğini planla, kontrol et!",
            font=("Segoe UI", 12),
            text_color="#94a3b8",
        ).pack(pady=(2, 25))

        # Giriş kartı
        kart = ctk.CTkFrame(
            self,
            corner_radius=16,
            fg_color="#0f766e",
            border_width=1,
            border_color="#14b8a6",
        )
        kart.pack(pady=10, padx=40, fill="x")

        ctk.CTkLabel(
            kart, text="🔐 Hesabına Giriş Yap", font=("Segoe UI", 16, "bold")
        ).pack(pady=(20, 15))

        self.kullanici_adi = ctk.CTkEntry(
            kart,
            width=320,
            height=42,
            placeholder_text="👤 Kullanıcı Adı",
            font=("Segoe UI", 14),
            corner_radius=10,
        )
        self.kullanici_adi.pack(pady=6)

        self.sifre = ctk.CTkEntry(
            kart,
            width=320,
            height=42,
            placeholder_text="🔒 Şifre",
            font=("Segoe UI", 14),
            corner_radius=10,
            show="•",
        )
        self.sifre.pack(pady=6)
        self.kullanici_adi.bind("<Return>", lambda e: self.sifre.focus())
        self.sifre.bind("<Return>", lambda e: self._giris_yap())

        # Beni hatırla
        self.beni_hatirla = ctk.CTkCheckBox(
            kart,
            text="Beni Hatırla",
            font=("Segoe UI", 13),
            checkbox_width=20,
            checkbox_height=20,
            border_color="#5eead4",
            fg_color="#14b8a6",
        )
        self.beni_hatirla.pack(pady=(10, 5))

        ctk.CTkButton(
            kart,
            text="🚀  Giriş Yap",
            width=280,
            height=42,
            font=("Segoe UI", 15, "bold"),
            fg_color="#0d9488",
            hover_color="#0f766e",
            corner_radius=10,
            command=self._giris_yap,
        ).pack(pady=(5, 5))

        ctk.CTkButton(
            kart,
            text="📝  Yeni Hesap Oluştur",
            width=280,
            height=36,
            font=("Segoe UI", 13),
            fg_color="transparent",
            hover_color="#0f766e",
            border_width=1,
            border_color="#14b8a6",
            corner_radius=10,
            command=self._kayit_ac,
        ).pack(pady=(0, 20))

        # Alt bilgi
        ctk.CTkLabel(
            self, text="v1.6.0 — Fineding", font=("Segoe UI", 10), text_color="#475569"
        ).pack(pady=(15, 0))

    def _giris_yap(self):
        kadi = self.kullanici_adi.get().strip()
        sifre = self.sifre.get()

        if not kadi or not sifre:
            messagebox.showwarning("Uyarı", "Kullanıcı adı ve şifre giriniz.")
            return

        # Kaba kuvvete karşı basit gecikme: art arda başarısız denemelerde
        # bekleme süresi artar (5 denemeden sonra hissedilir yavaşlar).
        basarisiz = getattr(self, "_basarisiz_deneme", 0)
        if basarisiz >= 5:
            import time
            bekleme = min(2 ** (basarisiz - 4), 30)
            time.sleep(bekleme)

        kullanici = self.db.kullanici_dogrula(kadi, sifre)
        if not kullanici:
            self._basarisiz_deneme = basarisiz + 1
            messagebox.showerror("Hata", "Kullanıcı adı veya şifre hatalı!")
            return
        self._basarisiz_deneme = 0

        # Beni hatırla
        if self.beni_hatirla.get():
            self.db.ayar_kaydet("beni_hatirla_kullanici", kadi)
        else:
            self.db.ayar_kaydet("beni_hatirla_kullanici", "")

        # Aktif kullanıcıyı kaydet
        self.db.ayar_kaydet("aktif_kullanici_id", str(kullanici["id"]))
        self.db.ayar_kaydet("aktif_kullanici_adi", kullanici["kullanici_adi"])

        self.kullanici = kullanici
        self.destroy()
        self.on_login_success(kullanici)

    def _kayit_ac(self):
        KayitPenceresi(self, self.db)


class KayitPenceresi(ctk.CTkToplevel):
    """Yeni kullanıcı kayıt penceresi."""

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("Yeni Hesap Oluştur")
        self.geometry("400x380")
        self.resizable(False, False)

        # Modal: arkaya kaçmaz, ana sayfaya tıklanamaz
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(self, text="📝 Yeni Hesap", font=("Segoe UI", 22, "bold")).pack(
            pady=20
        )

        self.ad_soyad = ctk.CTkEntry(
            self,
            width=300,
            height=38,
            placeholder_text="👤 Ad Soyad",
            font=("Segoe UI", 13),
        )
        self.ad_soyad.pack(pady=8)

        self.kullanici_adi = ctk.CTkEntry(
            self,
            width=300,
            height=38,
            placeholder_text="🔑 Kullanıcı Adı",
            font=("Segoe UI", 13),
        )
        self.kullanici_adi.pack(pady=8)

        self.sifre = ctk.CTkEntry(
            self,
            width=300,
            height=38,
            placeholder_text="🔒 Şifre",
            font=("Segoe UI", 13),
            show="•",
        )
        self.sifre.pack(pady=8)

        self.sifre_tekrar = ctk.CTkEntry(
            self,
            width=300,
            height=38,
            placeholder_text="🔒 Şifre (Tekrar)",
            font=("Segoe UI", 13),
            show="•",
        )
        self.sifre_tekrar.pack(pady=8)

        ctk.CTkButton(
            self,
            text="💾 Kaydol",
            width=240,
            height=38,
            fg_color="#2e8b57",
            command=self._kaydet,
        ).pack(pady=16)

    def _kaydet(self):
        kadi = self.kullanici_adi.get().strip()
        sifre = self.sifre.get()
        sifre2 = self.sifre_tekrar.get()
        ad = self.ad_soyad.get().strip()

        if not kadi or not sifre:
            messagebox.showwarning("Uyarı", "Kullanıcı adı ve şifre zorunludur.")
            return
        if sifre != sifre2:
            messagebox.showerror("Hata", "Şifreler eşleşmiyor!")
            return

        try:
            olustu = self.db.kullanici_kaydet(kadi, sifre, ad or kadi)
        except ValueError as e:
            # Şifre politikası ihlali (min uzunluk) veri katmanından gelir
            messagebox.showerror("Hata", str(e))
            return
        if olustu:
            messagebox.showinfo("Başarılı", "Hesap oluşturuldu! Giriş yapabilirsiniz.")
            self.destroy()
        else:
            messagebox.showerror("Hata", "Bu kullanıcı adı zaten kullanılıyor.")
