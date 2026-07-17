import logging
import sys
import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image as PILImage

from database import Database
from ui.money import para_formatla
from ui.ayarlar import AyarlarSayfasi
from ui.bakiye_widget import BakiyeWidget
from ui.butce import ButceSayfasi
from ui.dashboard import Dashboard
from ui.gelir import GelirSayfasi
from ui.gider import GiderSayfasi
from ui.giris import GirisEkrani
from ui.global_arama import GlobalAramaPenceresi
from ui.grafikler import GrafiklerSayfasi
from ui.hakkinda import HakkindaSayfasi
from ui.planlama import PlanlamaSayfasi

# Loglama
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

# Crash log handler
crash_log = log_dir / f"crash_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    filename=log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)


def _global_exception_handler(exc_type, exc_val, exc_tb):
    """Yakalanmayan hataları crash log'a yazar."""
    import traceback
    with open(crash_log, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"CRASH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n")
        traceback.print_exception(exc_type, exc_val, exc_tb, file=f)
    logger.critical("Uygulama çöktü!", exc_info=(exc_type, exc_val, exc_tb))


sys.excepthook = _global_exception_handler


def _asset_path(goreli_yol):
    """PyInstaller ve normal çalışma için asset yolunu çöz."""
    try:
        base = Path(sys._MEIPASS)
    except Exception:
        base = Path(__file__).parent
    return str(base / goreli_yol)


ctk.set_default_color_theme(_asset_path("assets/fineding_theme.json"))

# Bildirim sistemi
try:
    from plyer import notification

    HAS_NOTIFICATIONS = True
except ImportError:
    HAS_NOTIFICATIONS = False

# Sistem tepsisi
try:
    import pystray

    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def _bildirim_gonder(baslik, mesaj):
    """Windows toast bildirimi gönder."""
    try:
        if HAS_NOTIFICATIONS:
            notification.notify(
                title=baslik,
                message=mesaj,
                app_name="Fineding",
                timeout=8,
            )
    except Exception:
        pass  # Bildirim başarısız olursa sessizce devam et


def _tray_olustur(app):
    """Sistem tepsisi ikonu oluştur."""
    if not HAS_TRAY:
        return

    icon_path = Path(__file__).parent / "assets" / "app_icon.ico"
    if icon_path.exists():
        image = PILImage.open(icon_path)
    else:
        image = PILImage.new("RGB", (64, 64), (37, 99, 235))

    def on_show(icon, item):
        app.after(0, app.deiconify)

    def on_exit(icon, item):
        icon.stop()
        app.after(0, app._gercek_cikis)

    menu = pystray.Menu(
        pystray.MenuItem("Fineding'i Göster", on_show, default=True),
        pystray.MenuItem("Çıkış", on_exit),
    )
    icon = pystray.Icon("fineding", image, "Fineding", menu)

    def run_tray():
        icon.run()

    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()
    return icon


class FinedingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Fineding")
        self.geometry("1400x800")
        self.minsize(1200, 700)

        # System tray
        self.tray_icon = None

        # İkon
        icon_path = Path(__file__).parent / "assets" / "app_icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.db = Database()
        # Aktif oturum kullanıcısını veri katmanına bildir — tüm finans
        # sorguları bu kullanıcıyla filtrelenir (veri izolasyonu). Yetki
        # kararları da paylaşılan ayarlar tablosu yerine bu kimlikten verilir.
        kid = self.db.ayar_oku("aktif_kullanici_id", "1")
        try:
            self.db.oturum_ac(int(kid) if kid else 1)
        except (ValueError, TypeError):
            self.db.oturum_ac(1)
        kayitli_tema = self.db.ayar_oku("tema", "Dark")
        ctk.set_appearance_mode(kayitli_tema)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sol menü - logoya uygun teal arka plan
        self.menu = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#0f766e")
        self.menu.grid(row=0, column=0, sticky="ns")
        self.menu.grid_propagate(False)

        # İçerik alanı
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.menu_olustur()
        self.dashboard_ac()

        # Periyodik kontroller artık ayrı daemon thread yerine Tk'nin after()
        # zamanlamasıyla ana thread üzerinde çalışır: thread güvenliği sorunu
        # yok, self.db doğrudan (kullanıcıya özel) kullanılabilir ve hesap
        # değişiminde thread birikmez.
        self._bildirilen_borclar: set = set()
        self._kontrol_after_id = self.after(2000, self._periyodik_kontroller)

    # =====================================
    # SOL MENÜ
    # =====================================

    def menu_olustur(self):
        # Logo alanı - logomuzu göster
        logo_frame = ctk.CTkFrame(self.menu, fg_color="transparent")
        logo_frame.pack(pady=(25, 20), fill="x")

        icon_path = Path(__file__).parent / "assets" / "app_icon.ico"
        if icon_path.exists():
            self.logo_img = ctk.CTkImage(
                light_image=PILImage.open(icon_path),
                dark_image=PILImage.open(icon_path),
                size=(60, 60),
            )
            ctk.CTkLabel(logo_frame, image=self.logo_img, text="").pack()

        ctk.CTkLabel(
            logo_frame,
            text="FINEding",
            font=("Segoe UI", 20, "bold"),
            text_color="#ccfbf1",
        ).pack(pady=(4, 0))

        ctk.CTkLabel(
            logo_frame, text="Finans Takip", font=("Segoe UI", 11), text_color="#94a3b8"
        ).pack()

        # Ayraç
        ctk.CTkFrame(self.menu, height=1, fg_color="#334155").pack(
            fill="x", padx=20, pady=(0, 15)
        )

        # Menü butonları
        menu_ogeleri = [
            ("🏠", "Dashboard", "Ctrl+D", self.dashboard_ac),
            ("💰", "Gelir Ekle", "Ctrl+N", self.gelir_ac),
            ("💸", "Gider Ekle", "Ctrl+Shift+N", self.gider_ac),
            ("📊", "Grafikler", "Ctrl+Shift+G", self.grafikler_ac),
            ("📅", "Bütçe", "Ctrl+B", self.butce_ac),
            ("📋", "Planlama & Takip", "Ctrl+P", self.planlama_ac),
        ]

        self.menu_butonlari = []
        for ikon, metin, kisayol, komut in menu_ogeleri:
            btn = self._menu_butonu_olustur(ikon, metin, kisayol, komut)
            self.menu_butonlari.append(btn)

        # Alt ayraç
        ctk.CTkFrame(self.menu, height=1, fg_color="#334155").pack(
            fill="x", padx=20, pady=(15, 15), side="bottom"
        )

        # Ayarlar butonu (altta)
        self.btn_ayarlar = self._menu_butonu_olustur(
            "⚙️", "Ayarlar", "Ctrl+,", self.ayarlar_ac, alt=True
        )
        self._menu_butonu_olustur("ℹ️", "Hakkında", "", self.hakkinda_ac, alt=True)

        # Tema değiştirme butonu
        tema_frame = ctk.CTkFrame(self.menu, fg_color="transparent")
        tema_frame.pack(fill="x", padx=10, pady=3, side="bottom")
        tema_metni = (
            "  ☀️  Aydınlık Tema"
            if ctk.get_appearance_mode() == "Light"
            else "  🌙  Karanlık Tema"
        )
        self.tema_btn = ctk.CTkButton(
            tema_frame,
            text=tema_metni,
            font=("Segoe UI", 12),
            height=36,
            anchor="w",
            fg_color="transparent",
            hover_color="#0d9488",
            text_color="#cbd5e1",
            corner_radius=10,
            command=self._tema_degistir,
        )
        self.tema_btn.pack(fill="x")

        # Bakiye widget toggle
        widget_frame = ctk.CTkFrame(self.menu, fg_color="transparent")
        widget_frame.pack(fill="x", padx=10, pady=3, side="bottom")
        self.widget_btn = ctk.CTkButton(
            widget_frame,
            text="  💰  Bakiye Widget",
            font=("Segoe UI", 12),
            height=36,
            anchor="w",
            fg_color="transparent",
            hover_color="#0d9488",
            text_color="#cbd5e1",
            corner_radius=10,
            command=self._widget_toggle,
        )
        self.widget_btn.pack(fill="x")
        self._widget_acik = False
        self._bakiye_widget = None

        # Klavye kısayolları
        self.bind_all("<Control-f>", lambda e: self._global_arama_ac())
        self.bind_all("<Control-d>", lambda e: self.dashboard_ac())
        self.bind_all("<Control-n>", lambda e: self.gelir_ac())
        self.bind_all("<Control-N>", lambda e: self.gider_ac())
        self.bind_all("<Control-G>", lambda e: self.grafikler_ac())
        self.bind_all("<Control-b>", lambda e: self.butce_ac())
        self.bind_all("<Control-p>", lambda e: self.planlama_ac())
        self.bind_all("<Control-comma>", lambda e: self.ayarlar_ac())
        self.bind_all("<Control-q>", lambda e: self.cikis())

    def _menu_butonu_olustur(self, ikon, metin, kisayol, komut, alt=False):
        frame = ctk.CTkFrame(self.menu, fg_color="transparent")
        if alt:
            frame.pack(fill="x", padx=10, pady=3, side="bottom")
        else:
            frame.pack(fill="x", padx=10, pady=3)

        btn = ctk.CTkButton(
            frame,
            text=f"  {ikon}  {metin}",
            font=("Segoe UI", 14),
            height=42,
            anchor="w",
            fg_color="transparent",
            hover_color="#0d9488",
            text_color="#cbd5e1",
            corner_radius=10,
            command=komut,
        )
        btn.pack(fill="x")

        # Hover efekti
        def on_enter(e, b=btn):
            b.configure(fg_color="#0d9488", text_color="#ffffff")

        def on_leave(e, b=btn):
            b.configure(fg_color="transparent", text_color="#cbd5e1")

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        return btn

    # =====================================
    # SAYFA GEÇİŞİ
    # =====================================

    def _periyodik_kontroller(self):
        """Tekrarlayan işlemleri işler ve yaklaşan borç vadelerini bildirir.

        Ana thread üzerinde after() ile çalışır ve kendini yeniden zamanlar.
        """
        try:
            eklenenler = self.db.tekrarlayan_isle()
            for e in eklenenler:
                _bildirim_gonder(
                    "🔄 Tekrarlayan İşlem Eklendi",
                    f"{e['kategori']}: {para_formatla(e['tutar'], ondalik=0)} "
                    f"({e['tur']})",
                )
            if eklenenler:
                # Açık dashboard'u tazele
                try:
                    self.dashboard_ac()
                except Exception:
                    pass
        except Exception:
            logger.exception("Tekrarlayan işlem kontrolü başarısız")

        try:
            for b in self.db.yaklasan_borclar():
                if b["id"] in self._bildirilen_borclar:
                    continue  # bu oturumda zaten bildirildi (spam önleme)
                self._bildirilen_borclar.add(b["id"])
                kalan_gun = b["kalan_gun"]
                tutar = para_formatla(b["kalan_tutar"], ondalik=0)
                if kalan_gun < 0:
                    _bildirim_gonder(
                        "🔴 Vade Geçti!",
                        f"{b['aciklama']}\nKalan: {tutar}\n"
                        f"Vade: {b['vade_tarih']} (geçti)",
                    )
                else:
                    _bildirim_gonder(
                        "⏰ Ödeme Yaklaşıyor!",
                        f"{b['aciklama']}\nKalan: {tutar}\n"
                        f"Vade: {b['vade_tarih']} ({kalan_gun} gün)",
                    )
        except Exception:
            logger.exception("Borç vade kontrolü başarısız")

        # 30 dakikada bir tekrar
        self._kontrol_after_id = self.after(1800_000, self._periyodik_kontroller)

    def _guvenli_gecis(self, sayfa_sinifi, **kwargs):
        """Sayfa değiştir - öncekini yok et, yenisini oluştur."""
        # Önceki zamanlanmış geçişi iptal et
        if hasattr(self, "_gecis_after_id") and self._gecis_after_id is not None:
            self.after_cancel(self._gecis_after_id)
            self._gecis_after_id = None

        # Mevcut sayfayı temizle
        try:
            for widget in list(self.content.winfo_children()):
                widget.destroy()
        except Exception:
            pass

        # Yeni sayfayı hemen oluştur
        try:
            sayfa = sayfa_sinifi(self.content, self.db, **kwargs)
            sayfa.grid(row=0, column=0, sticky="nsew")
        except Exception as e:
            logger.error(f"Sayfa hatası: {sayfa_sinifi.__name__} - {e}")
            try:
                Dashboard(self.content, self.db).grid(row=0, column=0, sticky="nsew")
            except Exception:
                pass

    # =====================================
    # DASHBOARD
    # =====================================

    def dashboard_ac(self):
        self._guvenli_gecis(Dashboard)

    # =====================================
    # GELİR SAYFASI
    # =====================================

    def gelir_ac(self):
        self._guvenli_gecis(GelirSayfasi, dashboard_callback=self.dashboard_ac)

    # =====================================
    # GİDER SAYFASI
    # =====================================

    def gider_ac(self):
        self._guvenli_gecis(GiderSayfasi, dashboard_callback=self.dashboard_ac)

    # =====================================
    # BÜTÇE
    # =====================================

    def butce_ac(self):
        self._guvenli_gecis(ButceSayfasi, dashboard_callback=self.dashboard_ac)

    # =====================================
    # PLANLAMA
    # =====================================

    def planlama_ac(self):
        self._guvenli_gecis(PlanlamaSayfasi, dashboard_callback=self.dashboard_ac)

    # =====================================
    # GRAFİKLER
    # =====================================

    def grafikler_ac(self):
        self._guvenli_gecis(GrafiklerSayfasi, dashboard_callback=self.dashboard_ac)

    # =====================================
    # AYARLAR
    # =====================================

    def ayarlar_ac(self):
        self._guvenli_gecis(
            AyarlarSayfasi,
            dashboard_callback=self.dashboard_ac,
            hesap_degistir_callback=self.hesap_degistir,
        )

    # =====================================
    # HAKKINDA
    # =====================================

    def hakkinda_ac(self):
        self._guvenli_gecis(HakkindaSayfasi, dashboard_callback=self.dashboard_ac)

    # =====================================
    # ÇIKIŞ
    # =====================================

    def cikis(self):
        """X tuşuna basınca kapatmak yerine tepsiye küçült."""
        if not HAS_TRAY or not self.tray_icon:
            # Tepsi ikonu yoksa pencereyi gizlemenin geri dönüşü olmaz —
            # gerçekten kapat, aksi halde uygulama görünmez şekilde
            # arka planda takılı kalır.
            self._gercek_cikis()
            return

        self.withdraw()
        from plyer import notification

        try:
            notification.notify(
                title="Fineding",
                message="Arka planda çalışmaya devam ediyor.\nTamamen kapatmak için tepsi simgesine sağ tıklayın.",
                app_name="Fineding",
                timeout=4,
            )
        except Exception:
            pass

    def _gercek_cikis(self):
        """Tamamen kapat."""
        # Periyodik kontrol zamanlamasını durdur
        if getattr(self, "_kontrol_after_id", None) is not None:
            try:
                self.after_cancel(self._kontrol_after_id)
            except Exception:
                pass
            self._kontrol_after_id = None

        # Widget'ı kapat
        if hasattr(self, "_bakiye_widget") and self._bakiye_widget:
            try:
                self._bakiye_widget.kapat()
            except Exception:
                pass

        # Otomatik yedekle — yol çalışma dizinine göreli değil, uygulama
        # köküne sabit (farklı CWD'den başlatınca yedek kaybını önler)
        try:
            from datetime import datetime
            yedek_dir = Path(__file__).parent / "backups"
            yedek_dir.mkdir(exist_ok=True)
            yedek_adi = str(
                yedek_dir / f"oto_yedek_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            self.db.yedekle(yedek_adi)
            # Sadece son 10 yedeği tut
            yedekler = sorted(
                yedek_dir.glob("oto_yedek_*.db"), reverse=True
            )
            for eski in yedekler[10:]:
                try:
                    eski.unlink()
                    Path(str(eski) + ".hmac").unlink(missing_ok=True)
                    Path(str(eski) + ".sha256").unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            logger.exception("Otomatik yedekleme başarısız")

        self.db.close()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

    def _tema_degistir(self):
        """Aydınlık/Karanlık tema değiştir."""
        mevcut = ctk.get_appearance_mode()
        if mevcut == "Dark":
            ctk.set_appearance_mode("Light")
            self.tema_btn.configure(text="  ☀️  Aydınlık Tema")
            self.db.ayar_kaydet("tema", "Light")
        else:
            ctk.set_appearance_mode("Dark")
            self.tema_btn.configure(text="  🌙  Karanlık Tema")
            self.db.ayar_kaydet("tema", "Dark")

    def _global_arama_ac(self):
        """Ctrl+F: tüm işlem ve borçlarda anında arama penceresi."""
        if hasattr(self, "_arama_penceresi") and self._arama_penceresi is not None:
            try:
                if self._arama_penceresi.winfo_exists():
                    self._arama_penceresi.lift()
                    self._arama_penceresi.arama.focus_set()
                    return
            except Exception:
                pass
        self._arama_penceresi = GlobalAramaPenceresi(
            self, self.db, self.dashboard_ac, self.planlama_ac
        )

    def _ana_pencereyi_goster(self):
        """Ana pencereyi öne getirir (widget'tan 'Dashboard Aç' için)."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def _widget_toggle(self):
        """Bakiye widget'ını aç/kapat."""
        if self._widget_acik:
            self._widget_acik = False
            self.widget_btn.configure(
                text="  💰  Bakiye Widget",
                fg_color="transparent",
                border_width=0,
                text_color="#cbd5e1",
            )
            # Widget'ı kapat
            if hasattr(self, "_bakiye_widget") and self._bakiye_widget:
                try:
                    self._bakiye_widget.kapat()
                except Exception:
                    pass
                self._bakiye_widget = None
        else:
            self._widget_acik = True
            # Not: hover_color da "#0d9488" olduğu için "açık" durumunu ondan
            # ayrı bir renk + kenarlık ile göstermek gerekiyor, yoksa açık
            # hâli sıradan hover efektiyle aynı görünüyor ve fark edilmiyor.
            self.widget_btn.configure(
                text="  ✅  Widget Açık",
                fg_color="#0f766e",
                border_width=2,
                border_color="#2dd4bf",
                text_color="#ffffff",
            )
            self._bakiye_widget = BakiyeWidget(self, self.db, ana_pencere_callback=self._ana_pencereyi_goster)

    def hesap_degistir(self):
        """Oturumu kapatıp giriş ekranına dön.

        Önceden baslat()'ı özyinelemeli çağırıyordu; bu, mainloop'ları iç içe
        biriktiriyor ve her seferinde yeni kontrol thread'leri başlatıyordu.
        Artık sadece bir bayrak set edip pencereyi kapatır; dıştaki baslat()
        döngüsü giriş ekranını yeniden gösterir (tek, düz mainloop).
        """
        self._hesap_degistir_istendi = True
        self.db.ayar_kaydet("aktif_kullanici_id", "")
        self._gercek_cikis()


def baslat():
    """Uygulamayı giriş ekranıyla başlat.

    Giriş ekranı ve ana pencere mainloop'ları iç içe DEĞİL, sıralı çalışır:
    her tur giriş ekranını gösterir, giriş başarılıysa ana pencereyi açar,
    kullanıcı 'Hesap Değiştir' derse döngü başa döner. Böylece mainloop ve
    kontrol thread'i birikmesi olmaz.
    """
    logger.info("Fineding başlatılıyor...")
    while True:
        db = Database()
        giris = GirisEkrani(db, None)
        giris.protocol(
            "WM_DELETE_WINDOW", lambda g=giris: setattr(g, "_kapatildi", True) or g.destroy()
        )
        giris.mainloop()
        kullanici = getattr(giris, "kullanici", None)
        db.close()
        if not kullanici:
            break  # kullanıcı giriş yapmadan kapattı

        app = FinedingApp()
        app.protocol("WM_DELETE_WINDOW", app.cikis)
        app.tray_icon = _tray_olustur(app)
        _bildirim_gonder(
            "Fineding'e Hoş Geldiniz! 👋",
            f"Merhaba {kullanici['ad_soyad']}, finansal takibiniz başladı.\n"
            "Ödemeler yaklaştığında sizi uyaracağız.",
        )
        app.mainloop()

        if not getattr(app, "_hesap_degistir_istendi", False):
            break  # normal çıkış — döngüden çık


if __name__ == "__main__":
    baslat()
