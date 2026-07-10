import logging
import threading
from datetime import date, datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image as PILImage

from database import Database
from ui.ayarlar import AyarlarSayfasi
from ui.bakiye_widget import BakiyeWidget
from ui.butce import ButceSayfasi
from ui.dashboard import Dashboard
from ui.gelir import GelirSayfasi
from ui.gider import GiderSayfasi
from ui.giris import GirisEkrani
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


import sys
sys.excepthook = _global_exception_handler

ctk.set_default_color_theme(
    str(Path(__file__).parent / "assets" / "fineding_theme.json")
)

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


def _borc_kontrol_thread(db_path: str):
    """Arka planda borç vadesi yaklaşanları kontrol eder."""
    import sqlite3
    import time

    while True:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            bugun = date.today()
            # Vadesine 3 gün veya daha az kalmış aktif borçları bul
            cur.execute(
                "SELECT aciklama, kalan_tutar, vade_tarih FROM borclar "
                "WHERE durum='Aktif' AND vade_tarih != '' AND vade_tarih IS NOT NULL"
            )
            for aciklama, kalan, vade_str in cur.fetchall():
                try:
                    # Tarih formatları: GG.AA.YYYY veya YYYY-MM-DD
                    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                        try:
                            vade = datetime.strptime(vade_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        continue
                    kalan_gun = (vade - bugun).days
                    if 0 <= kalan_gun <= 3:
                        _bildirim_gonder(
                            "⏰ Ödeme Yaklaşıyor!",
                            f"{aciklama}\nKalan: {kalan:,.0f} ₺\n"
                            f"Vade: {vade_str} ({kalan_gun} gün)",
                        )
                    elif kalan_gun < 0:
                        _bildirim_gonder(
                            "🔴 Vade Geçti!",
                            f"{aciklama}\nKalan: {kalan:,.0f} ₺\n"
                            f"Vade: {vade_str} (geçti)",
                        )
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass
        time.sleep(1800)  # 30 dakikada bir kontrol


def _tekrarlayan_kontrol_thread(db_path: str):
    """Arka planda tekrarlayan işlemleri kontrol eder ve otomatik ekler."""
    import sqlite3
    import time

    while True:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            bugun_gun = date.today().day
            cur.execute(
                "SELECT tur, kategori, aciklama, tutar FROM tekrarlayan "
                "WHERE aktif=1 AND gun=?",
                (bugun_gun,),
            )
            for tur, kategori, aciklama, tutar in cur.fetchall():
                # Bugün zaten eklenmiş mi kontrol et
                bugun_str = date.today().strftime("%Y-%m-%d")
                cur.execute(
                    "SELECT COUNT(*) FROM islemler WHERE tarih=? AND tur=? AND "
                    "kategori=? AND aciklama=? AND tutar=?",
                    (bugun_str, tur, kategori, aciklama or "", tutar),
                )
                if cur.fetchone()[0] == 0:
                    cur.execute(
                        "INSERT INTO islemler (tarih, tur, kategori, aciklama, tutar, etiketler) "
                        "VALUES (?,?,?,?,?, 'tekrarlayan')",
                        (bugun_str, tur, kategori, aciklama, tutar),
                    )
                    conn.commit()
                    _bildirim_gonder(
                        "🔄 Tekrarlayan İşlem Eklendi",
                        f"{kategori}: {tutar:,.0f} ₺ ({tur})",
                    )
            conn.close()
        except Exception:
            pass
        time.sleep(3600)  # Saatte bir kontrol


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
        ctk.set_appearance_mode("dark")

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
        self.tema_btn = ctk.CTkButton(
            tema_frame,
            text="  🌙  Karanlık Tema",
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

        # Klavye kısayolları
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
        self.withdraw()
        if HAS_TRAY:
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
        # Otomatik yedekle
        try:
            from datetime import datetime
            yedek_adi = f"backups/oto_yedek_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            self.db.yedekle(yedek_adi)
            # Sadece son 10 yedeği tut
            import glob
            yedekler = sorted(glob.glob("backups/oto_yedek_*.db"), reverse=True)
            for eski in yedekler[10:]:
                try:
                    Path(eski).unlink()
                except Exception:
                    pass
        except Exception:
            pass

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
        else:
            ctk.set_appearance_mode("Dark")
            self.tema_btn.configure(text="  🌙  Karanlık Tema")

    def _widget_toggle(self):
        """Bakiye widget'ını aç/kapat."""
        if self._widget_acik:
            self._widget_acik = False
            self.widget_btn.configure(text="  💰  Bakiye Widget", fg_color="transparent")
        else:
            self._widget_acik = True
            self.widget_btn.configure(text="  💰  Widget Açık", fg_color="#0d9488")
            BakiyeWidget.baslat(self.db)

    def hesap_degistir(self):
        """Oturumu kapatıp giriş ekranına dön."""
        self.db.ayar_kaydet("beni_hatirla_kullanici", "")
        self.db.ayar_kaydet("aktif_kullanici_id", "")
        self.db.close()
        self.destroy()
        baslat()


def baslat():
    """Uygulamayı giriş ekranıyla başlat."""
    logger.info("Fineding başlatılıyor...")
    db = Database()
    logger.info("Veritabanı bağlantısı kuruldu")

    # Arka plan borç kontrolü başlat
    import database as db_module

    kontrol = threading.Thread(
        target=_borc_kontrol_thread,
        args=(str(db_module.DB_PATH),),
        daemon=True,
    )
    kontrol.start()

    # Tekrarlayan işlem kontrolü
    tekrar_kontrol = threading.Thread(
        target=_tekrarlayan_kontrol_thread,
        args=(str(db_module.DB_PATH),),
        daemon=True,
    )
    tekrar_kontrol.start()

    def on_login(kullanici):
        app = FinedingApp()
        app.protocol("WM_DELETE_WINDOW", app.cikis)

        # Sistem tepsisi
        app.tray_icon = _tray_olustur(app)

        # İlk bildirim
        _bildirim_gonder(
            "Fineding'e Hoş Geldiniz! 👋",
            f"Merhaba {kullanici['ad_soyad']}, finansal takibiniz başladı.\n"
            "Ödemeler yaklaştığında sizi uyaracağız.",
        )
        app.mainloop()

    giris = GirisEkrani(db, on_login)
    giris.protocol("WM_DELETE_WINDOW", lambda: (db.close(), giris.destroy()))
    giris.mainloop()


if __name__ == "__main__":
    baslat()
