import tempfile
import unittest
from pathlib import Path

import database as db_module


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_module.DB_FOLDER = Path(self.temp_dir.name)
        db_module.DB_PATH = db_module.DB_FOLDER / "test_finans.db"
        self.db = db_module.Database()

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_transaction_update_budget_and_settings(self):
        self.db.gelir_ekle("01.01.2026", "Maaş", "Test gelir", 1000)
        self.db.guncelle_islem(1, "02.01.2026", "Gelir", "Maaş", "Güncellendi", 1200)

        islem = self.db.tum_islemler()[0]
        # dates are normalized to ISO YYYY-MM-DD
        self.assertEqual(islem[1], "2026-01-02")
        self.assertEqual(islem[5], 1200.0)

        self.db.kaydet_butce(1, 2026, "Yemek", 500)
        butce = self.db.butce_listele(1, 2026)[0]
        self.assertEqual(butce[0], "Yemek")
        self.assertEqual(butce[1], 500.0)

        self.db.ayar_kaydet("tema", "dark")
        self.assertEqual(self.db.ayar_oku("tema"), "dark")

    def test_budget_status_summary(self):
        self.db.gelir_ekle("01.01.2026", "Maaş", "Test gelir", 1000)
        self.db.gider_ekle("05.01.2026", "Yemek", "Market", 200)
        self.db.kaydet_butce(1, 2026, "Yemek", 300)

        durum = self.db.butce_durumu(1, 2026)
        self.assertEqual(len(durum), 1)
        self.assertEqual(durum[0]["kategori"], "Yemek")
        self.assertEqual(durum[0]["butce"], 300.0)
        self.assertEqual(durum[0]["harcanan"], 200.0)
        self.assertEqual(durum[0]["kalan"], 100.0)

    def test_user_authentication(self):
        # İlk kullanıcıyı oluştur (admin)
        self.assertTrue(self.db.kullanici_kaydet("admin", "admin123", "Yönetici"))
        kullanici = self.db.kullanici_dogrula("admin", "admin123")
        self.assertIsNotNone(kullanici)
        assert kullanici is not None
        self.assertEqual(kullanici["kullanici_adi"], "admin")
        # İlk kullanıcı admin olmalı
        self.assertTrue(self.db.kullanici_admin_mi(kullanici["id"]))

        # Yanlış şifre
        self.assertIsNone(self.db.kullanici_dogrula("admin", "yanlis123"))

        # Yeni kullanıcı
        self.assertTrue(self.db.kullanici_kaydet("test", "test1234", "Test Kullanıcı"))
        self.assertFalse(self.db.kullanici_kaydet("test", "test1234", "Dup"))

        k = self.db.kullanici_dogrula("test", "test1234")
        self.assertIsNotNone(k)
        assert k is not None
        self.assertEqual(k["ad_soyad"], "Test Kullanıcı")

        # Şifre değiştir (admin başkasının şifresini değiştirebilir)
        self.db.kullanici_sifre_degistir(k["id"], "yenisifre")
        self.assertIsNone(self.db.kullanici_dogrula("test", "test1234"))
        self.assertIsNotNone(self.db.kullanici_dogrula("test", "yenisifre"))

        # Admin kendini silemez
        self.assertFalse(self.db.kullanici_sil(1))
        # Normal kullanıcı silinebilir
        self.assertTrue(self.db.kullanici_sil(k["id"]))

    def test_sifre_politikasi(self):
        """Kısa şifreler veri katmanında reddedilmeli (#38)."""
        with self.assertRaises(ValueError):
            self.db.kullanici_kaydet("kisa", "123", "Kısa")

    def test_yetki_kontrolu(self):
        """Admin olmayan kullanıcı silme/başkasının şifresini değiştiremez (#6)."""
        import database as dbm
        self.db.kullanici_kaydet("admin", "admin123", "Admin")
        self.db.kullanici_kaydet("ayse", "ayse1234", "Ayşe")
        # Aktif kullanıcıyı normal kullanıcıya (id=2) çevir
        self.db.oturum_ac(2)
        with self.assertRaises(dbm.YetkiHatasi):
            self.db.kullanici_sil(1)
        with self.assertRaises(dbm.YetkiHatasi):
            self.db.kullanici_sifre_degistir(1, "baskasinin")
        # Kendi şifresini değiştirebilir
        self.db.kullanici_sifre_degistir(2, "yenisifre")

    def test_kullanici_izolasyonu(self):
        """Her kullanıcı yalnızca kendi işlemlerini görmeli (#1)."""
        self.db.oturum_ac(1)
        self.db.gelir_ekle("01.07.2026", "Maaş", "Admin geliri", 5000)
        self.db.oturum_ac(2)
        self.db.gelir_ekle("01.07.2026", "Maaş", "Ayşe geliri", 3000)

        self.assertEqual(len(self.db.tum_islemler()), 1)
        self.assertEqual(self.db.toplam_gelir(), 3000.0)
        self.db.oturum_ac(1)
        self.assertEqual(len(self.db.tum_islemler()), 1)
        self.assertEqual(self.db.toplam_gelir(), 5000.0)
        # Kullanıcı 1, kullanıcı 2'nin işlemini silememeli
        ayse_islem = None
        self.db.oturum_ac(2)
        ayse_islem = self.db.tum_islemler()[0][0]
        self.db.oturum_ac(1)
        self.db.sil(ayse_islem)  # başka kullanıcının kaydı — etkisiz
        self.db.oturum_ac(2)
        self.assertEqual(len(self.db.tum_islemler()), 1)

    def test_tutar_parse_binlik_nokta(self):
        """İçe aktarım Türk binlik ayracını 1000x küçük okumamalı.

        _tutar_parse'ın eski kopyası 'tek nokta' dalını hiç ele almıyordu:
        float("45.000") = 45.0 → maaş satırı 45 TL olarak içe aktarılıyordu.
        Artık ui.money.para_parse ile tek kaynaktan ayrıştırılır.
        """
        self.assertEqual(self.db._tutar_parse("45.000"), 45000.0)
        self.assertEqual(self.db._tutar_parse("1.500"), 1500.0)
        self.assertEqual(self.db._tutar_parse("1.234,56"), 1234.56)
        self.assertEqual(self.db._tutar_parse("1,234.56"), 1234.56)
        self.assertEqual(self.db._tutar_parse("12.5"), 12.5)
        self.assertEqual(self.db._tutar_parse("-1.500"), -1500.0)
        self.assertEqual(self.db._tutar_parse(""), 0.0)
        self.assertEqual(self.db._tutar_parse(None), 0.0)
        with self.assertRaises(ValueError):
            self.db._tutar_parse("abc")

    def test_tutar_parse_money_ile_ayni(self):
        """İki ayrıştırıcı ayrışırsa aynı metin farklı tutara çevrilir."""
        from ui.money import para_parse
        for ham in ("1500", "1.500", "1.234,56", "1,234.56", "12,5", "12.5",
                    "1.500.000,00", "-45.000"):
            with self.subTest(ham=ham):
                self.assertEqual(self.db._tutar_parse(ham), para_parse(ham))

    def test_tasarruf_katki_izolasyonu(self):
        """Katkı başka kullanıcının hedefine yazılamamalı."""
        self.db.kullanici_kaydet("admin", "admin123", "Admin")
        self.db.kullanici_kaydet("ayse", "ayse1234", "Ayşe")

        self.db.oturum_ac(2)
        self.db.tasarruf_hedefi_ekle("Ayşe tatil", 10000, "01.12.2026")
        ayse_hedef = self.db.tasarruf_hedefleri_listele()[0]["id"]

        # Kullanıcı 1, Ayşe'nin hedefine katkı yapamamalı
        self.db.oturum_ac(1)
        with self.assertRaises(ValueError):
            self.db.tasarruf_katki_ekle(ayse_hedef, 500)
        # Ayşe'nin birikimi değişmemeli ve kullanıcı 1'e işlem yazılmamalı
        self.assertEqual(len(self.db.tum_islemler()), 0)
        self.db.oturum_ac(2)
        self.assertEqual(
            self.db.tasarruf_hedefleri_listele()[0]["biriken_tutar"], 0.0
        )

    def test_borc_odemeleri_izolasyonu(self):
        """Ödeme geçmişi başka kullanıcının borcu için sızmamalı."""
        self.db.kullanici_kaydet("admin", "admin123", "Admin")
        self.db.kullanici_kaydet("ayse", "ayse1234", "Ayşe")

        self.db.oturum_ac(2)
        borc_id = self.db.borc_ekle(
            "Borç", "Ayşe borcu", "Mehmet", 1000, 1000, "01.07.2026", "01.12.2026"
        )
        self.db.borc_odeme_yap(borc_id, 250, "15.07.2026")
        self.assertEqual(len(self.db.borc_odemeleri(borc_id)), 1)

        # Kullanıcı 1 aynı borç id'siyle geçmişi görememeli
        self.db.oturum_ac(1)
        self.assertEqual(self.db.borc_odemeleri(borc_id), [])

    def test_borc_fazla_odeme_kirpilir(self):
        """Kalanı aşan ödeme geçmişe kırpılmış yazılmalı."""
        borc_id = self.db.borc_ekle(
            "Borç", "Kredi", "Banka", 1000, 100, "01.07.2026", "01.12.2026"
        )
        # Kalan 100 TL iken 5000 girilse bile geçmişe yalnızca 100 yazılmalı;
        # islem_olustur=True verildiğinde işlem de 100'e kırpılmalı (4900 değil)
        self.db.borc_odeme_yap(borc_id, 5000, "15.07.2026", islem_olustur=True)

        odemeler = self.db.borc_odemeleri(borc_id)
        self.assertEqual(len(odemeler), 1)
        self.assertEqual(odemeler[0]["tutar"], 100.0)
        self.assertEqual(self.db.toplam_gider(), 100.0)
        borc = self.db.borclari_listele("Tümü")[0]
        self.assertEqual(borc["kalan_tutar"], 0.0)
        self.assertEqual(borc["durum"], "Ödendi")

    def test_borc_odeme_bakiyeye_dokunmaz(self):
        """Model B: ödeme varsayılan olarak bakiyeye/gider'e yansımamalı."""
        borc_id = self.db.borc_ekle(
            "Borç", "Kredi", "Banka", 1000, 1000, "01.07.2026", "01.12.2026"
        )
        self.db.borc_odeme_yap(borc_id, 400, "15.07.2026")  # varsayılan kapalı

        # Bakiye/gider ETKİLENMEMELİ (çift sayım yok)
        self.assertEqual(self.db.toplam_gider(), 0.0)
        self.assertEqual(self.db.bakiye(), 0.0)
        # Ama borç durumu güncellenmiş ve geçmişe yazılmış olmalı
        self.assertEqual(len(self.db.borc_odemeleri(borc_id)), 1)
        self.assertEqual(self.db.borclari_listele("Tümü")[0]["kalan_tutar"], 600.0)

    def test_borc_net_pozisyon(self):
        """Net pozisyon: alacak - borç, tablo filtresinden bağımsız."""
        self.db.borc_ekle("Alacak", "Mehmet'e", "Mehmet", 5000, 5000,
                          "01.07.2026", "01.12.2026")
        self.db.borc_ekle("Borç", "Bankaya", "Banka", 2000, 2000,
                          "01.07.2026", "01.12.2026")
        poz = self.db.borc_net_pozisyon()
        self.assertEqual(poz["alacak"], 5000.0)
        self.assertEqual(poz["borc"], 2000.0)
        self.assertEqual(poz["net"], 3000.0)

    def test_borc_odemeler_fk_cascade(self):
        """FK: borclar'dan doğrudan silince ödemeleri cascade ile silinmeli."""
        borc_id = self.db.borc_ekle(
            "Borç", "Kredi", "Banka", 1000, 1000, "01.07.2026", "01.12.2026"
        )
        self.db.borc_odeme_yap(borc_id, 250, "15.07.2026")
        self.assertEqual(len(self.db.borc_odemeleri(borc_id)), 1)

        # borc_sil'i ATLA, doğrudan borclar'dan sil → FK cascade devrede olmalı
        self.db.cursor.execute("DELETE FROM borclar WHERE id=?", (borc_id,))
        self.db.conn.commit()
        self.db.cursor.execute(
            "SELECT COUNT(*) FROM borc_odemeler WHERE borc_id=?", (borc_id,)
        )
        self.assertEqual(self.db.cursor.fetchone()[0], 0)

    def test_borc_odemeler_fk_migrasyonu(self):
        """v5 FK'siz DB'de yetim ödeme temizlenip FK eklenmeli."""
        eski_dir = tempfile.TemporaryDirectory()
        self.addCleanup(eski_dir.cleanup)
        eski_yol = Path(eski_dir.name) / "v5.db"

        db_module.DB_PATH = eski_yol
        hazir = db_module.Database()
        # FK'siz eski tabloyu taklit et: yeni tabloyu düşürüp FK'siz kur
        hazir.conn.executescript("""
            DROP TABLE borc_odemeler;
            CREATE TABLE borc_odemeler(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                borc_id INTEGER NOT NULL, tarih TEXT NOT NULL, tutar REAL NOT NULL);
            INSERT INTO borclar (id, tur, aciklama, kisi, toplam_tutar, kalan_tutar,
                baslangic_tarih, vade_tarih, durum, kullanici_id)
                VALUES (1,'Borç','X','Y',100,100,'2026-07-01','2026-12-01','Aktif',1);
            INSERT INTO borc_odemeler (borc_id, tarih, tutar) VALUES (1,'2026-07-05',50);
            INSERT INTO borc_odemeler (borc_id, tarih, tutar) VALUES (999,'2026-07-05',30);
        """)
        hazir.conn.execute("PRAGMA user_version=5")
        hazir.conn.commit()
        hazir.close()

        yeni = db_module.Database()
        self.addCleanup(yeni.close)
        # FK eklenmiş olmalı
        self.assertTrue(
            yeni.conn.execute("PRAGMA foreign_key_list(borc_odemeler)").fetchall()
        )
        # Geçerli ödeme kalmış, yetim (borc_id=999) atılmış olmalı
        n = yeni.conn.execute("SELECT COUNT(*) FROM borc_odemeler").fetchone()[0]
        self.assertEqual(n, 1)

    def test_borc_sil_odemeleri_de_siler(self):
        """Borç silinince ödeme geçmişi yetim kalmamalı."""
        borc_id = self.db.borc_ekle(
            "Borç", "Kredi", "Banka", 1000, 1000, "01.07.2026", "01.12.2026"
        )
        self.db.borc_odeme_yap(borc_id, 250, "15.07.2026")
        self.db.borc_sil(borc_id)

        self.db.cursor.execute(
            "SELECT COUNT(*) FROM borc_odemeler WHERE borc_id=?", (borc_id,)
        )
        self.assertEqual(self.db.cursor.fetchone()[0], 0)

    def test_profil_guncelleme_yetkisi(self):
        """Normal kullanıcı başkasının profilini değiştirememeli."""
        import database as dbm
        self.db.kullanici_kaydet("admin", "admin123", "Admin")
        self.db.kullanici_kaydet("ayse", "ayse1234", "Ayşe")

        self.db.oturum_ac(2)
        with self.assertRaises(dbm.YetkiHatasi):
            self.db.kullanici_profil_guncelle(1, "Ele geçirildi")
        self.assertEqual(self.db.kullanici_ad_oku(1), "Admin")
        # Kendi profilini değiştirebilmeli
        self.db.kullanici_profil_guncelle(2, "Ayşe Yılmaz")
        self.assertEqual(self.db.kullanici_ad_oku(2), "Ayşe Yılmaz")

    def test_transaction_rollback(self):
        """Çok adımlı yazma yarıda kesilirse kısmi değişiklik kalmamalı."""
        self.db.gelir_ekle("01.07.2026", "Maaş", "Başlangıç", 1000)
        onceki = len(self.db.tum_islemler())

        with self.assertRaises(RuntimeError):
            with self.db._transaction():
                self.db.cursor.execute(
                    "INSERT INTO islemler (tarih, tur, kategori, aciklama, "
                    "tutar, kullanici_id) VALUES (?,?,?,?,?,?)",
                    ("2026-07-02", "Gider", "Test", "Yarım kalan", 50, 1),
                )
                raise RuntimeError("simüle edilmiş hata")

        self.assertEqual(len(self.db.tum_islemler()), onceki)

    def test_giris_kilidi_kalici(self):
        """Başarısız deneme sayacı DB'de tutulmalı, örnek değişkeninde değil."""
        self.db.kullanici_kaydet("ayse", "dogrusifre", "Ayşe")
        self.assertEqual(self.db.giris_kilit_saniyesi("ayse"), 0)

        for _ in range(5):
            self.assertIsNone(self.db.kullanici_dogrula("ayse", "yanlis"))

        # 5. denemeden sonra kilit devrede
        self.assertGreater(self.db.giris_kilit_saniyesi("ayse"), 0)

        # Yeni bir Database örneği (uygulama yeniden başlatıldı) sıfırlamamalı
        yeni = db_module.Database()
        try:
            self.assertGreater(yeni.giris_kilit_saniyesi("ayse"), 0)
        finally:
            yeni.close()

    def test_basarili_giris_sayaci_sifirlar(self):
        """Doğru şifreyle giriş kilidi kaldırmalı."""
        self.db.kullanici_kaydet("ayse", "dogrusifre", "Ayşe")
        for _ in range(3):
            self.db.kullanici_dogrula("ayse", "yanlis")

        self.assertIsNotNone(self.db.kullanici_dogrula("ayse", "dogrusifre"))
        self.db.cursor.execute(
            "SELECT basarisiz_deneme FROM kullanicilar WHERE kullanici_adi=?",
            ("ayse",),
        )
        self.assertEqual(self.db.cursor.fetchone()[0], 0)

    def test_eski_semadan_migrasyon(self):
        """v0 şemalı bir DB veri kaybetmeden güncel şemaya yükseltilmeli."""
        import sqlite3
        eski_dir = tempfile.TemporaryDirectory()
        self.addCleanup(eski_dir.cleanup)
        eski_yol = Path(eski_dir.name) / "eski.db"

        c = sqlite3.connect(eski_yol)
        c.executescript("""
        CREATE TABLE islemler(id INTEGER PRIMARY KEY AUTOINCREMENT,
          tarih TEXT NOT NULL, tur TEXT NOT NULL, kategori TEXT NOT NULL,
          aciklama TEXT, tutar REAL NOT NULL);
        CREATE TABLE butceler(id INTEGER PRIMARY KEY AUTOINCREMENT, ay INTEGER,
          yil INTEGER, kategori TEXT, tutar REAL, UNIQUE(ay,yil,kategori));
        CREATE TABLE planlanan(id INTEGER PRIMARY KEY AUTOINCREMENT, ay INTEGER,
          yil INTEGER, kategori TEXT, tur TEXT, aciklama TEXT, tutar REAL);
        CREATE TABLE borclar(id INTEGER PRIMARY KEY AUTOINCREMENT, tur TEXT,
          aciklama TEXT, kisi TEXT, toplam_tutar REAL, kalan_tutar REAL,
          baslangic_tarih TEXT, vade_tarih TEXT, durum TEXT DEFAULT 'Aktif');
        CREATE TABLE tekrarlayan(id INTEGER PRIMARY KEY AUTOINCREMENT, tur TEXT,
          kategori TEXT, aciklama TEXT, tutar REAL, gun INTEGER,
          aktif INTEGER DEFAULT 1);
        CREATE TABLE tasarruf_hedefleri(id INTEGER PRIMARY KEY AUTOINCREMENT,
          ad TEXT, hedef_tutar REAL, biriken_tutar REAL DEFAULT 0,
          hedef_tarih TEXT);
        CREATE TABLE kullanicilar(id INTEGER PRIMARY KEY AUTOINCREMENT,
          kullanici_adi TEXT UNIQUE NOT NULL, sifre_hash TEXT NOT NULL,
          ad_soyad TEXT, olusturma_tarihi TEXT NOT NULL);
        INSERT INTO islemler (tarih,tur,kategori,aciklama,tutar)
          VALUES ('2026-01-15','Gelir','Maaş','Ocak maaşı',45000.0);
        INSERT INTO islemler (tarih,tur,kategori,aciklama,tutar)
          VALUES ('2026-01-20','Gider','Market','Alışveriş',1250.50);
        INSERT INTO kullanicilar (kullanici_adi,sifre_hash,ad_soyad,olusturma_tarihi)
          VALUES ('mevcut','x','Mevcut','2026-01-01');
        PRAGMA user_version=0;
        """)
        c.commit()
        c.close()

        db_module.DB_PATH = eski_yol
        eski_db = db_module.Database()
        self.addCleanup(eski_db.close)

        self.assertEqual(
            eski_db.conn.execute("PRAGMA user_version").fetchone()[0],
            db_module.SCHEMA_VERSION,
        )
        for tablo, kolon in (
            ("islemler", "kullanici_id"), ("islemler", "etiketler"),
            ("planlanan", "aktarim_tarihi"), ("tekrarlayan", "son_islenen_donem"),
            ("kullanicilar", "basarisiz_deneme"),
        ):
            kolonlar = {
                r[1] for r in eski_db.conn.execute(f"PRAGMA table_info({tablo})")
            }
            self.assertIn(kolon, kolonlar, f"{tablo}.{kolon} eklenmedi")

        # Mevcut veri korunmalı ve admin'e (id=1) atanmalı
        eski_db.oturum_ac(1)
        self.assertEqual(len(eski_db.tum_islemler()), 2)
        self.assertEqual(eski_db.toplam_gelir(), 45000.0)
        self.assertEqual(eski_db.toplam_gider(), 1250.50)

    def test_toplu_sil_tek_geri_al_ile_donuyor(self):
        """Toplu silme tek geri-al biriminde tamamen geri gelmeli."""
        for i in range(5):
            self.db.gider_ekle(f"0{i+1}.07.2026", "Market", f"Alışveriş {i}", 100)
        idler = [s[0] for s in self.db.tum_islemler()]
        self.assertEqual(len(idler), 5)

        silinen = self.db.sil_toplu(idler)
        self.assertEqual(silinen, 5)
        self.assertEqual(len(self.db.tum_islemler()), 0)

        # Tek "Geri Al" 5'ini birden getirmeli (eskiden yalnızca 1 dönüyordu)
        self.assertEqual(self.db.geri_al(), 5)
        self.assertEqual(len(self.db.tum_islemler()), 5)
        self.assertEqual(self.db.toplam_gider(), 500.0)

    def test_geri_al_yigini_sirayla_calisir(self):
        """Art arda silmelerde her geri-al bir öncekini getirmeli."""
        self.db.gider_ekle("01.07.2026", "Market", "Birinci", 100)
        self.db.gider_ekle("02.07.2026", "Market", "İkinci", 200)
        birinci, ikinci = [s[0] for s in self.db.tum_islemler()][::-1]

        self.db.sil(birinci)
        self.db.sil(ikinci)
        self.assertEqual(len(self.db.tum_islemler()), 0)

        # İki ayrı geri-al iki kaydı da getirmeli (tek slot değil, yığın)
        self.assertEqual(self.db.geri_al(), 1)
        self.assertEqual(self.db.geri_al(), 1)
        self.assertEqual(len(self.db.tum_islemler()), 2)
        self.assertEqual(self.db.geri_al(), 0)

    def test_islem_ara_donem_ve_arama_birlikte(self):
        """Dönem filtresi aramayı yok saymamalı; ikisi birlikte uygulanmalı."""
        from datetime import date, timedelta
        bugun = date.today()
        dun = bugun - timedelta(days=1)

        self.db.gider_ekle(bugun.strftime("%d.%m.%Y"), "Market", "bugun kahve", 50)
        self.db.gider_ekle(bugun.strftime("%d.%m.%Y"), "Market", "bugun ekmek", 20)
        self.db.gider_ekle("01.01.2020", "Market", "eski kahve", 999)

        # Yalnızca dönem
        self.assertEqual(len(self.db.islem_ara(donem="bugun")), 2)
        # Dönem + arama birlikte
        sonuc = self.db.islem_ara("kahve", donem="bugun")
        self.assertEqual(len(sonuc), 1)
        self.assertEqual(sonuc[0][4], "bugun kahve")
        # Dönemsiz arama eskiyi de bulmalı
        self.assertEqual(len(self.db.islem_ara("kahve")), 2)
        # Dönem + tür birlikte
        self.assertEqual(len(self.db.islem_ara(tur="Gelir", donem="bugun")), 0)
        # dun değişkeni hafta sınırında kullanılır
        self.assertLessEqual(dun, bugun)

    def test_zayif_hash_asla_uretilmez(self):
        """bcrypt yoksa sessizce tuzsuz SHA-256 üretilmemeli, hata verilmeli."""
        import database as dbm
        orijinal = dbm._HAS_BCRYPT
        dbm._HAS_BCRYPT = False
        try:
            with self.assertRaises(RuntimeError):
                dbm._sifre_hashla("herhangibirsifre")
        finally:
            dbm._HAS_BCRYPT = orijinal

    def test_uretilen_hash_bcrypt_ve_tuzlu(self):
        """Yeni hash'ler bcrypt olmalı ve aynı şifre farklı hash vermeli."""
        import database as dbm
        h1 = dbm._sifre_hashla("aynisifre123")
        h2 = dbm._sifre_hashla("aynisifre123")
        self.assertTrue(h1.startswith("$2"))
        self.assertNotEqual(h1, h2, "Tuz yok: aynı şifre aynı hash veriyor")
        self.assertTrue(dbm._sifre_dogrula("aynisifre123", h1))
        self.assertFalse(dbm._sifre_dogrula("yanlissifre", h1))

    def test_eski_sha256_hash_girise_izin_verip_yukseltir(self):
        """Mevcut kullanıcılar kilitlenmemeli; hash bcrypt'e yükselmeli."""
        import hashlib
        import database as dbm
        self.db.kullanici_kaydet("eski", "eskisifre123", "Eski")
        # Kullanıcıyı bilerek eski (bcrypt öncesi) hash'e geri çevir
        legacy = hashlib.sha256(b"Fineding2024!" + b"eskisifre123").hexdigest()
        self.db.cursor.execute(
            "UPDATE kullanicilar SET sifre_hash=? WHERE kullanici_adi=?",
            (legacy, "eski"),
        )
        self.db.conn.commit()

        self.assertIsNotNone(self.db.kullanici_dogrula("eski", "eskisifre123"))
        self.db.cursor.execute(
            "SELECT sifre_hash FROM kullanicilar WHERE kullanici_adi=?", ("eski",)
        )
        yeni_hash = self.db.cursor.fetchone()[0]
        self.assertTrue(
            yeni_hash.startswith("$2"), "Eski hash bcrypt'e yükseltilmedi"
        )
        self.assertNotEqual(yeni_hash, legacy)
        self.assertTrue(dbm._HAS_BCRYPT)

    def test_hmac_anahtari_sabit_degere_dusmez(self):
        """Anahtar yazılamıyorsa gömülü sabite düşmemeli, hata vermeli."""
        import database as dbm
        from unittest import mock
        with mock.patch.object(
            dbm.Path, "write_bytes", side_effect=OSError("salt-okunur")
        ), mock.patch.object(dbm.Path, "exists", return_value=False):
            with self.assertRaises(dbm.HmacAnahtarHatasi):
                dbm._hmac_anahtari()

    def test_kategori_izolasyonu(self):
        """Özel kategoriler kullanıcılar arası sızmamalı."""
        self.db.kullanici_kaydet("admin", "admin123", "Admin")
        self.db.kullanici_kaydet("ayse", "ayse1234", "Ayşe")

        self.db.oturum_ac(1)
        self.db.kategori_ekle("Gider", "AdminÖzel")
        self.db.oturum_ac(2)
        self.db.kategori_ekle("Gider", "AyşeÖzel")

        # Her kullanıcı yalnızca kendi kategorisini görmeli
        self.assertEqual(self.db.kategorileri_getir("Gider"), ["AyşeÖzel"])
        self.db.oturum_ac(1)
        self.assertEqual(self.db.kategorileri_getir("Gider"), ["AdminÖzel"])

    def test_kategori_migrasyonu_global_admine_tasinir(self):
        """v3 DB'deki global kategoriler admin'e (id=1) taşınmalı."""
        eski_dir = tempfile.TemporaryDirectory()
        self.addCleanup(eski_dir.cleanup)
        eski_yol = Path(eski_dir.name) / "v3.db"

        # Mevcut şemayı kur, sonra user_version'ı 3'e düşürüp global kategori yaz
        tmp = db_module.DB_PATH
        db_module.DB_PATH = eski_yol
        hazir = db_module.Database()
        hazir.conn.execute(
            "INSERT INTO ayarlar (anahtar, deger) VALUES ('kategoriler_gider','Kripto,Kira')"
        )
        hazir.conn.execute("PRAGMA user_version=3")
        hazir.conn.commit()
        hazir.close()

        # Yeniden aç → v4 migrasyonu çalışmalı
        yeni = db_module.Database()
        self.addCleanup(yeni.close)
        db_module.DB_PATH = tmp

        self.assertEqual(
            yeni.conn.execute("PRAGMA user_version").fetchone()[0],
            db_module.SCHEMA_VERSION,
        )
        # Global anahtar silinmiş, admin'in anahtarına taşınmış olmalı
        self.assertIsNone(
            yeni.conn.execute(
                "SELECT deger FROM ayarlar WHERE anahtar='kategoriler_gider'"
            ).fetchone()
        )
        yeni.oturum_ac(1)
        self.assertEqual(yeni.kategorileri_getir("Gider"), ["Kripto", "Kira"])

    def test_ice_aktarim_ayristir_ve_ekle(self):
        """Ayrıştırma (DB'siz) ile ekleme (DB) ayrı çalışmalı — UI thread'i için."""
        import csv as _csv
        yol = Path(self.temp_dir.name) / "islemler.csv"
        with open(yol, "w", newline="", encoding="utf-8-sig") as f:
            w = _csv.writer(f)
            w.writerow(["tarih", "tur", "kategori", "aciklama", "tutar"])
            w.writerow(["01.07.2026", "Gelir", "Maaş", "Temmuz", "10.000"])
            w.writerow(["05.07.2026", "Gider", "Market", "Alışveriş", "1.250,50"])

        # Ayrıştırma DB'ye dokunmadan satırları döndürür
        satirlar = self.db.csv_satirlarini_oku(str(yol))
        self.assertEqual(len(satirlar), 2)
        self.assertEqual(len(self.db.tum_islemler()), 0)  # henüz eklenmedi

        # Ekleme ana thread'de yapılır
        eklenen = self.db.satirlari_ice_aktar(satirlar)
        self.assertEqual(eklenen, 2)
        self.assertEqual(self.db.toplam_gelir(), 10000.0)
        self.assertEqual(self.db.toplam_gider(), 1250.50)

    def test_planlanan_kopyala_atomik(self):
        """Plan kopyalama atomik olmalı; üzerine yazma onay gerektirmeli."""
        self.db.planlanan_ekle(6, 2026, "Maaş", "Gelir", "Haziran", 15000)
        self.db.planlanan_ekle(6, 2026, "Kira", "Gider", "Ev", 5000)

        # Hedef boşken kopyala
        sonuc = self.db.planlanan_kopyala(6, 2026, 7, 2026)
        self.assertEqual(sonuc["kopyalanan"], 2)
        self.assertEqual(len(self.db.planlanan_listele(7, 2026)), 2)

        # Hedef doluyken uzerine_yaz=False → -1 (çağıran onay istemeli), veri değişmez
        sonuc2 = self.db.planlanan_kopyala(6, 2026, 7, 2026)
        self.assertEqual(sonuc2["kopyalanan"], -1)
        self.assertEqual(len(self.db.planlanan_listele(7, 2026)), 2)

        # uzerine_yaz=True → eskiyi sil, yeniyi koy (net sonuç yine 2)
        sonuc3 = self.db.planlanan_kopyala(6, 2026, 7, 2026, uzerine_yaz=True)
        self.assertEqual(sonuc3["kopyalanan"], 2)
        self.assertEqual(sonuc3["silinen"], 2)
        self.assertEqual(len(self.db.planlanan_listele(7, 2026)), 2)

        # Kaynak yokken
        self.assertEqual(
            self.db.planlanan_kopyala(1, 2020, 2, 2020)["kopyalanan"], 0
        )

    def test_tekrarlayan_yeni_kural_geriye_donuk_eklemez(self):
        """Günü geçmiş yeni kural, bu ayı geriye dönük eklememeli (çift kayıt)."""
        from datetime import date
        bugun = date.today()
        # Günü kesin geçmiş bir kural: gün=1 (ayın 2'sinden sonra her zaman geçmiş)
        if bugun.day < 2:
            self.skipTest("Ayın 1'inde bu senaryo test edilemez")
        self.db.tekrarlayan_ekle("Gider", "Kira", "Ev", 5000, 1)
        eklenenler = self.db.tekrarlayan_isle(bugun)
        # Yeni kural bu ayı geriye dönük EKLEMEMELİ
        self.assertEqual(len(eklenenler), 0)
        self.assertEqual(len(self.db.tum_islemler()), 0)

    def test_tekrarlayan_gunu_gelmemis_kural_bu_ay_calisir(self):
        """Günü henüz gelmemiş yeni kural, günü gelince bu ay çalışmalı."""
        from datetime import date
        bugun = date.today()
        # Bugünden sonraki bir günü hedefle (bu ay henüz gelmemiş)
        if bugun.day >= 28:
            self.skipTest("Ay sonunda ileri gün seçilemez")
        ileri_gun = bugun.day + 1
        self.db.tekrarlayan_ekle("Gider", "Fatura", "Elektrik", 300, ileri_gun)
        # Gün henüz gelmedi → bugün işlenince eklenmez
        self.assertEqual(len(self.db.tekrarlayan_isle(bugun)), 0)
        # Gün geldiğinde (o günü simüle et) → eklenir
        gelecek = bugun.replace(day=ileri_gun)
        self.assertEqual(len(self.db.tekrarlayan_isle(gelecek)), 1)

    def test_sifre_dogru_mu_sayaci_artirmaz(self):
        """Şifre doğrulama (değiştirme akışı) kilit sayacını beslememeli."""
        # ayse ilk kayıt → id=1
        self.db.kullanici_kaydet("ayse", "dogrusifre", "Ayşe")
        self.db.oturum_ac(1)
        # Yanlış şifreyi 6 kez doğrula → kilit TETİKLENMEMELİ
        for _ in range(6):
            self.assertFalse(self.db.sifre_dogru_mu("yanlis"))
        self.assertEqual(self.db.giris_kilit_saniyesi("ayse"), 0)
        # Doğru şifre True dönmeli
        self.assertTrue(self.db.sifre_dogru_mu("dogrusifre"))

    def test_planlama(self):
        self.db.planlanan_ekle(7, 2026, "Maaş", "Gelir", "Temmuz maaşı", 15000)
        self.db.planlanan_ekle(7, 2026, "Kira", "Gider", "Ev kirası", 5000)

        liste = self.db.planlanan_listele(7, 2026)
        self.assertEqual(len(liste), 2)

        ozet = self.db.planlanan_ozet(7, 2026)
        self.assertEqual(ozet["Gelir"], 15000.0)
        self.assertEqual(ozet["Gider"], 5000.0)

        # Güncelle
        self.db.planlanan_guncelle(liste[0][0], "Maaş", "Gelir", "Güncel", 16000)
        ozet2 = self.db.planlanan_ozet(7, 2026)
        self.assertEqual(ozet2["Gelir"], 16000.0)

        # Sil
        self.db.planlanan_sil(liste[0][0])
        self.assertEqual(len(self.db.planlanan_listele(7, 2026)), 1)

    def test_borclar(self):
        borc_id = self.db.borc_ekle(
            "Borç", "Kredi Kartı", "Banka A", 10000, 7500, "01.06.2026", "01.12.2026"
        )
        self.db.borc_ekle(
            "Alacak", "Maaş", "Şirket", 20000, 20000, "01.07.2026", "01.07.2026"
        )

        aktif = self.db.borclari_listele("Aktif")
        self.assertEqual(len(aktif), 2)

        # Güncelle
        self.db.borc_guncelle(borc_id, 5000, "Aktif")
        odendi = self.db.borclari_listele("Ödendi")
        self.assertEqual(len(odendi), 0)

        self.db.borc_guncelle(borc_id, 0, "Ödendi")
        odendi = self.db.borclari_listele("Ödendi")
        self.assertEqual(len(odendi), 1)

        toplam = self.db.borc_toplam("Aktif")
        self.assertEqual(toplam, 20000.0)

    def test_undo(self):
        self.db.gelir_ekle("01.07.2026", "Maaş", "Test", 5000)
        self.assertEqual(len(self.db.tum_islemler()), 1)
        self.db.sil(1)
        self.assertEqual(len(self.db.tum_islemler()), 0)

        # Geri al
        self.assertTrue(self.db.geri_al())
        self.assertEqual(len(self.db.tum_islemler()), 1)

        # İkinci geri al başarısız
        self.assertFalse(self.db.geri_al())

    def test_undo_etiket_korur(self):
        """Geri al, silinen işlemin etiketlerini kaybetmemeli."""
        self.db.gelir_ekle("01.07.2026", "Maaş", "Etiketli işlem", 5000, "önemli, iş")
        kayit = self.db.islem_ara("Etiketli")[0]
        self.db.sil(kayit[0])
        self.assertTrue(self.db.geri_al())
        geri_gelen = self.db.islem_ara("Etiketli")[0]
        self.assertEqual(geri_gelen[6], "önemli, iş")

    def test_yedekle_wal_checkpoint(self):
        """Yedekleme, WAL modunda henüz checkpoint edilmemiş veriyi kaçırmamalı."""
        import sqlite3

        self.db.gelir_ekle("01.07.2026", "Maaş", "WAL testi", 12345)

        yedek_yol = Path(self.temp_dir.name) / "yedek.db"
        self.db.yedekle(str(yedek_yol))

        # Yedeği bağımsız bir bağlantıyla aç — orijinal bağlantı hâlâ
        # açıkken bile checkpoint edilmiş veri görünmeli.
        yedek_conn = sqlite3.connect(str(yedek_yol))
        try:
            cur = yedek_conn.cursor()
            cur.execute("SELECT COUNT(*) FROM islemler WHERE aciklama='WAL testi'")
            self.assertEqual(cur.fetchone()[0], 1)
        finally:
            yedek_conn.close()

    def test_search(self):
        self.db.gelir_ekle("01.07.2026", "Maaş", "Ocak maaşı", 10000)
        self.db.gider_ekle("05.07.2026", "Market", "Haftalık alışveriş", 500)

        # Metin arama
        sonuc = self.db.islem_ara("maaş")
        self.assertEqual(len(sonuc), 1)

        # Tür filtresi
        sonuc = self.db.islem_ara(tur="Gider")
        self.assertEqual(len(sonuc), 1)
        self.assertEqual(sonuc[0][3], "Market")

        # Boş arama hepsini getirir
        sonuc = self.db.islem_ara()
        self.assertEqual(len(sonuc), 2)

    def test_import_csv(self):
        """CSV içe aktarma testi."""
        import csv as csv_mod
        csv_yol = Path(self.temp_dir.name) / "islemler.csv"
        with open(csv_yol, "w", newline="", encoding="utf-8") as f:
            writer = csv_mod.writer(f)
            writer.writerow(["tarih", "tur", "kategori", "aciklama", "tutar", "etiketler"])
            writer.writerow(["01.07.2026", "Gelir", "Maaş", "İçe aktarılan", "2500", "test"])
            writer.writerow(["02.07.2026", "Gider", "Market", "Alışveriş", "300", ""])
            writer.writerow(["", "Geçersiz", "", "", "", ""])  # geçersiz satır, atlanmalı

        eklenen = self.db.import_csv(str(csv_yol))
        self.assertEqual(eklenen, 2)
        sonuc = self.db.islem_ara("İçe aktarılan")
        self.assertEqual(len(sonuc), 1)
        self.assertEqual(sonuc[0][6], "test")

    def test_import_excel(self):
        """Excel içe aktarma testi."""
        from openpyxl import Workbook
        xlsx_yol = Path(self.temp_dir.name) / "islemler.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["Tarih", "Tür", "Kategori", "Açıklama", "Tutar", "Etiket"])
        ws.append(["03.07.2026", "Gider", "Kira", "Temmuz kirası", 9000, "ev"])
        wb.save(xlsx_yol)

        eklenen = self.db.import_excel(str(xlsx_yol))
        self.assertEqual(eklenen, 1)
        sonuc = self.db.islem_ara("Temmuz kirası")
        self.assertEqual(len(sonuc), 1)
        self.assertEqual(sonuc[0][6], "ev")

    def test_etiket(self):
        """İşlem etiketleme: ekleme, etikete göre arama ve güncelleme."""
        self.db.gelir_ekle("01.07.2026", "Maaş", "Ocak maaşı", 10000, "iş, önemli")
        sonuc = self.db.islem_ara("önemli")
        self.assertEqual(len(sonuc), 1)
        self.assertEqual(sonuc[0][6], "iş, önemli")

        islem_id = sonuc[0][0]
        self.db.guncelle_islem(
            islem_id, "01.07.2026", "Gelir", "Maaş", "Ocak maaşı", 10000, "güncellendi"
        )
        guncel = self.db.islem_ara("güncellendi")
        self.assertEqual(len(guncel), 1)
        self.assertEqual(guncel[0][6], "güncellendi")

    def test_bcrypt_hash(self):
        """Bcrypt hash'leme ve doğrulama testi."""
        from database import _sifre_hashla, _sifre_dogrula
        sifre = "test123"
        hash_deger = _sifre_hashla(sifre)
        self.assertTrue(hash_deger.startswith("$2b$") or len(hash_deger) == 64)
        self.assertTrue(_sifre_dogrula(sifre, hash_deger))
        self.assertFalse(_sifre_dogrula("yanlis", hash_deger))

    def test_legacy_sha256_sifre_dogrulama(self):
        """bcrypt mevcutken bile eski (bcrypt öncesi) SHA-256 hash'ler doğrulanabilmeli."""
        import hashlib
        from database import _sifre_dogrula
        sifre = "eskisifre123"
        eski_hash = hashlib.sha256(b"Fineding2024!" + sifre.encode()).hexdigest()
        self.assertTrue(_sifre_dogrula(sifre, eski_hash))
        self.assertFalse(_sifre_dogrula("yanlissifre", eski_hash))

    def test_islem_log(self):
        """CRUD işlemlerinin log'a kaydedildiğini test et."""
        self.db.gelir_ekle("05.07.2026", "Maaş", "Log test", 500)
        self.db.gider_ekle("05.07.2026", "Market", "Log test", 100)

        cur = self.db.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM islem_log")
        self.assertGreaterEqual(cur.fetchone()[0], 2)

    def test_tekrarlayan(self):
        """Tekrarlayan işlem ekleme/listeleme/silme testi."""
        self.db.tekrarlayan_ekle("Gider", "Kira", "Ev kirası", 3000, 1)
        self.db.tekrarlayan_ekle("Gelir", "Maaş", "", 15000, 1)

        liste = self.db.tekrarlayan_listele()
        self.assertEqual(len(liste), 2)
        tutarlar = {t["tutar"] for t in liste}
        self.assertIn(3000.0, tutarlar)
        self.assertIn(15000.0, tutarlar)

        # Aktif/Deaktif
        self.db.tekrarlayan_toggle(liste[1]["id"])
        liste2 = self.db.tekrarlayan_listele()
        self.assertEqual(liste2[1]["aktif"], 0)

        # Sil
        self.db.tekrarlayan_sil(liste[0]["id"])
        self.assertEqual(len(self.db.tekrarlayan_listele()), 1)

    def test_tasarruf_hedefi(self):
        """Tasarruf hedefi ekleme, katkı ve ilerleme testi."""
        hedef_id = self.db.tasarruf_hedefi_ekle("Tatil", 10000, "31.12.2026")
        liste = self.db.tasarruf_hedefleri_listele()
        self.assertEqual(len(liste), 1)
        self.assertEqual(liste[0]["hedef_tutar"], 10000.0)
        self.assertEqual(liste[0]["biriken_tutar"], 0.0)

        self.db.tasarruf_katki_ekle(hedef_id, 2500)
        self.db.tasarruf_katki_ekle(hedef_id, 1000)
        guncel = self.db.tasarruf_hedefleri_listele()[0]
        self.assertEqual(guncel["biriken_tutar"], 3500.0)

        # Negatife düşmemeli
        self.db.tasarruf_katki_ekle(hedef_id, -100000)
        sonuc = self.db.tasarruf_hedefleri_listele()[0]
        self.assertEqual(sonuc["biriken_tutar"], 0.0)

        self.db.tasarruf_hedefi_sil(hedef_id)
        self.assertEqual(len(self.db.tasarruf_hedefleri_listele()), 0)

    def test_tasarruf_katki_islem_olusturur(self):
        """Tasarruf katkısı ana işlem listesine Gider olarak yansımalı (#4)."""
        hedef_id = self.db.tasarruf_hedefi_ekle("Tatil", 10000)
        self.db.gelir_ekle("01.07.2026", "Maaş", "Maaş", 10000)
        bakiye_once = self.db.bakiye()

        self.db.tasarruf_katki_ekle(hedef_id, 2500)
        # Katkı Gider olarak kaydedilmeli, bakiye 2500 azalmalı
        self.assertEqual(self.db.bakiye(), bakiye_once - 2500)
        gider = self.db.islem_ara("Tasarruf", "Gider")
        self.assertEqual(len(gider), 1)
        self.assertEqual(gider[0][5], 2500.0)

        # Geri çekme Gelir olarak yansımalı, biriken bakiyeyle sınırlı
        self.db.tasarruf_katki_ekle(hedef_id, -1000)
        self.assertEqual(self.db.bakiye(), bakiye_once - 1500)
        hedef = self.db.tasarruf_hedefleri_listele()[0]
        self.assertEqual(hedef["biriken_tutar"], 1500.0)

    def test_tasarruf_katki_islemsiz(self):
        """islem_olustur=False iken sadece biriken güncellenir (eski test uyumu)."""
        hedef_id = self.db.tasarruf_hedefi_ekle("Araba", 50000)
        self.db.tasarruf_katki_ekle(hedef_id, 3000, islem_olustur=False)
        self.assertEqual(len(self.db.tum_islemler()), 0)
        self.assertEqual(
            self.db.tasarruf_hedefleri_listele()[0]["biriken_tutar"], 3000.0
        )

    def test_borc_odeme_yap(self):
        """Ödeme kalanı düşürür; islem_olustur=True ise gider işlemi de üretir."""
        borc_id = self.db.borc_ekle(
            "Borç", "Kredi Kartı", "Banka", 10000, 10000, "01.06.2026", "01.12.2026"
        )
        # Bilinçli tercihle işlem de oluştur
        self.db.borc_odeme_yap(borc_id, 3000, "15.07.2026", islem_olustur=True)

        borc = self.db.borclari_listele("Aktif")[0]
        self.assertEqual(borc["kalan_tutar"], 7000.0)
        gider = self.db.islem_ara("ödemesi", "Gider")
        self.assertEqual(len(gider), 1)
        self.assertEqual(gider[0][5], 3000.0)
        gecmis = self.db.borc_odemeleri(borc_id)
        self.assertEqual(len(gecmis), 1)

        # Tam ödeme → Ödendi (varsayılan: işlem üretmeden)
        self.db.borc_odeme_yap(borc_id, 7000, "20.07.2026")
        self.assertEqual(len(self.db.borclari_listele("Ödendi")), 1)

    def test_borc_bakiye_ayirma_migrasyonu(self):
        """v4 DB'deki eski borc-odeme işlemleri bakiyeden temizlenmeli."""
        eski_dir = tempfile.TemporaryDirectory()
        self.addCleanup(eski_dir.cleanup)
        eski_yol = Path(eski_dir.name) / "v4.db"

        db_module.DB_PATH = eski_yol
        hazir = db_module.Database()
        # Eski model: borc-odeme etiketli bir Gider ve normal bir Gider
        hazir.conn.execute(
            "INSERT INTO islemler (tarih, tur, kategori, aciklama, tutar, "
            "etiketler, kullanici_id) VALUES "
            "('2026-07-01','Gider','Borç/Alacak','Borç ödemesi',500,'borc-odeme',1),"
            "('2026-07-02','Gider','Market','Alışveriş',200,'',1)"
        )
        hazir.conn.execute("PRAGMA user_version=4")
        hazir.conn.commit()
        hazir.close()

        yeni = db_module.Database()
        self.addCleanup(yeni.close)
        yeni.oturum_ac(1)
        # borc-odeme işlemi silinmiş, normal gider kalmış olmalı
        self.assertEqual(yeni.toplam_gider(), 200.0)
        self.assertEqual(yeni.migrate_silinen_borc_islem, 1)

    def test_borc_tarih_normalize(self):
        """Borç tarihleri ISO'ya normalize edilip doğru sıralanmalı (#18)."""
        self.db.borc_ekle("Borç", "A", "", 100, 100, "01.06.2026", "15.12.2026")
        self.db.borc_ekle("Borç", "B", "", 100, 100, "01.06.2026", "05.01.2027")
        self.db.borc_ekle("Borç", "C", "", 100, 100, "01.06.2026", "20.11.2026")
        vadeler = [b["vade_tarih"] for b in self.db.borclari_listele("Aktif")]
        # ISO formatında ve kronolojik sırada olmalı
        self.assertEqual(vadeler, ["2026-11-20", "2026-12-15", "2027-01-05"])

    def test_plani_aktar_mukerrer_koruma(self):
        """Plan aktarımı ikinci çağrıda kalemleri tekrar aktarmamalı (#33)."""
        self.db.planlanan_ekle(7, 2026, "Maaş", "Gelir", "Maaş", 15000)
        self.db.planlanan_ekle(7, 2026, "Kira", "Gider", "Kira", 5000)

        sonuc1 = self.db.plani_aktar(7, 2026, "01.07.2026")
        self.assertEqual(sonuc1["aktarilan"], 2)
        self.assertEqual(sonuc1["atlanan"], 0)
        self.assertEqual(len(self.db.tum_islemler()), 2)

        # İkinci aktarım hiçbir şey eklememeli
        sonuc2 = self.db.plani_aktar(7, 2026, "01.07.2026")
        self.assertEqual(sonuc2["aktarilan"], 0)
        self.assertEqual(sonuc2["atlanan"], 2)
        self.assertEqual(len(self.db.tum_islemler()), 2)

    def test_import_turk_format_tutar(self):
        """İçe aktarma Türk formatlı tutarları (1.234,56) okuyabilmeli (#40)."""
        self.assertEqual(self.db._tutar_parse("1.234,56"), 1234.56)
        self.assertEqual(self.db._tutar_parse("12,5"), 12.5)
        self.assertEqual(self.db._tutar_parse("1500"), 1500.0)
        self.assertEqual(self.db._tutar_parse("1,234.56"), 1234.56)

    def test_geri_yukle_gecersiz_dosya_reddeder(self):
        """Geri yükleme SQLite olmayan dosyayı reddetmeli (#5)."""
        kotu = Path(self.temp_dir.name) / "kotu.db"
        kotu.write_text("bu bir sqlite dosyası değil", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.db.geri_yukle(str(kotu))
        # Orijinal veri korunmalı — bağlantı hâlâ çalışıyor olmalı
        self.db.gelir_ekle("01.07.2026", "Maaş", "Sağlam", 100)
        self.assertEqual(len(self.db.tum_islemler()), 1)

    def test_geri_yukle_gecerli_yedek(self):
        """Geçerli yedek geri yüklenebilmeli ve veriyi getirmeli (#5)."""
        self.db.gelir_ekle("01.07.2026", "Maaş", "Yedek verisi", 999)
        yedek = Path(self.temp_dir.name) / "gecerli.db"
        self.db.yedekle(str(yedek))
        self.db.sil(1)
        self.assertEqual(len(self.db.tum_islemler()), 0)
        self.db.geri_yukle(str(yedek))
        self.assertEqual(len(self.db.tum_islemler()), 1)

    def test_like_joker_kacis(self):
        """LIKE aramasında % ve _ joker olarak yorumlanmamalı (#41)."""
        self.db.gelir_ekle("01.07.2026", "Maaş", "100% bonus", 500)
        self.db.gelir_ekle("01.07.2026", "Maaş", "normal", 500)
        # '%' düz metin olarak aranmalı, her şeyi getirmemeli
        sonuc = self.db.islem_ara("100%")
        self.assertEqual(len(sonuc), 1)
        self.assertEqual(sonuc[0][4], "100% bonus")

    def test_migration_user_version(self):
        """Migration sonrası user_version güncellenmeli (#25)."""
        v = self.db.conn.execute("PRAGMA user_version").fetchone()[0]
        self.assertGreaterEqual(v, 1)

    def test_index_var(self):
        """Sık kullanılan kolonlara index eklenmiş olmalı (#26)."""
        idx = {
            r[0]
            for r in self.db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        self.assertIn("idx_islemler_tarih", idx)
        self.assertIn("idx_islemler_tur_tarih", idx)

    def test_tekrarlayan_isle_ilk_ay(self):
        """Günü gelmiş tekrarlayan işlem işlenmeli, gelmemiş beklemeli (#7)."""
        from datetime import date
        # Kural önceki ayda oluşturuldu (bugun=Haziran); Temmuz'da işlenmeli.
        self.db.tekrarlayan_ekle("Gider", "Kira", "Ev", 5000, 1,
                                 bugun=date(2026, 6, 20))
        # Ayın 15'inde çalıştır — günü (1) geçmiş, eklenmeli
        eklenen = self.db.tekrarlayan_isle(bugun=date(2026, 7, 15))
        self.assertEqual(len(eklenen), 1)
        self.assertEqual(len(self.db.tum_islemler()), 1)
        # Aynı gün tekrar çalıştır — mükerrer eklememeli
        eklenen2 = self.db.tekrarlayan_isle(bugun=date(2026, 7, 20))
        self.assertEqual(len(eklenen2), 0)
        self.assertEqual(len(self.db.tum_islemler()), 1)

    def test_tekrarlayan_isle_gunu_gelmemis(self):
        """Günü henüz gelmemiş kural bu ay işlenmemeli (#7)."""
        from datetime import date
        self.db.tekrarlayan_ekle("Gider", "Kira", "Ev", 5000, 20,
                                 bugun=date(2026, 6, 25))
        eklenen = self.db.tekrarlayan_isle(bugun=date(2026, 7, 5))
        self.assertEqual(len(eklenen), 0)

    def test_tekrarlayan_isle_kacan_aylar(self):
        """Uygulama aylarca kapalı kalırsa kaçan aylar telafi edilmeli (#7)."""
        from datetime import date
        # Kural Nisan'da oluşturuldu; Mayıs'ta ilk kez işlenir, sonra kaçan
        # Haziran/Temmuz telafi edilir.
        self.db.tekrarlayan_ekle("Gider", "Kira", "Ev", 5000, 1,
                                 bugun=date(2026, 4, 20))
        self.db.tekrarlayan_isle(bugun=date(2026, 5, 10))
        # 3 ay sonra aç — Haziran ve Temmuz da eklenmeli
        eklenen = self.db.tekrarlayan_isle(bugun=date(2026, 7, 10))
        self.assertEqual(len(eklenen), 2)
        self.assertEqual(len(self.db.tum_islemler()), 3)

    def test_tekrarlayan_isle_ay_sonu(self):
        """31. günde tanımlı kural, Şubat'ta ayın son gününe kaymalı (#7)."""
        from datetime import date
        self.db.tekrarlayan_ekle("Gider", "Fatura", "F", 100, 31,
                                 bugun=date(2026, 1, 31))
        eklenen = self.db.tekrarlayan_isle(bugun=date(2026, 2, 28))
        self.assertEqual(len(eklenen), 1)
        # 2026 Şubat 28 gün — tarih 2026-02-28 olmalı
        self.assertEqual(self.db.tum_islemler()[0][1], "2026-02-28")

    def test_csv_guvenli(self):
        """Formül enjeksiyonu tetikleyen hücreler tek tırnakla kaçışlanmalı (#13)."""
        from database import csv_guvenli
        self.assertEqual(csv_guvenli("=HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(csv_guvenli("+1+1"), "'+1+1")
        self.assertEqual(csv_guvenli("-2"), "'-2")
        self.assertEqual(csv_guvenli("@cmd"), "'@cmd")
        # Normal metin dokunulmaz
        self.assertEqual(csv_guvenli("Market"), "Market")
        self.assertEqual(csv_guvenli(1500), 1500)

    def test_upgrade_on_login(self):
        """Eski SHA-256 hash başarılı girişte bcrypt'e yükseltilmeli (#14)."""
        import hashlib
        import database as dbm
        if not dbm._HAS_BCRYPT:
            self.skipTest("bcrypt yok")
        # Elle eski SHA-256 hash'li kullanıcı ekle
        eski = hashlib.sha256(b"Fineding2024!" + b"gizli123").hexdigest()
        self.db.conn.execute(
            "INSERT INTO kullanicilar (kullanici_adi, sifre_hash, ad_soyad, "
            "olusturma_tarihi) VALUES ('eski', ?, 'Eski', '2026-01-01')",
            (eski,),
        )
        self.db.conn.commit()
        # Giriş başarılı olmalı
        self.assertIsNotNone(self.db.kullanici_dogrula("eski", "gizli123"))
        # Hash artık bcrypt olmalı
        yeni_hash = self.db.conn.execute(
            "SELECT sifre_hash FROM kullanicilar WHERE kullanici_adi='eski'"
        ).fetchone()[0]
        self.assertTrue(yeni_hash.startswith("$2"))
        # Yeni hash'le hâlâ giriş yapılabilmeli
        self.assertIsNotNone(self.db.kullanici_dogrula("eski", "gizli123"))

    def test_yedek_hmac_kurcalama(self):
        """Kurcalanmış yedek HMAC kontrolüyle reddedilmeli (#15)."""
        self.db.gelir_ekle("01.07.2026", "Maaş", "Test", 100)
        yedek = Path(self.temp_dir.name) / "y.db"
        self.db.yedekle(str(yedek))
        self.assertTrue(Path(str(yedek) + ".hmac").exists())
        # Yedeği boz
        with open(yedek, "ab") as f:
            f.write(b"BOZUK")
        with self.assertRaises(ValueError):
            self.db.geri_yukle(str(yedek))

    def test_butce_kopyala(self):
        """Önceki ayın bütçesi yeni aya kopyalanabilmeli (#34)."""
        self.db.kaydet_butce(6, 2026, "Market", 3000)
        self.db.kaydet_butce(6, 2026, "Kira", 8000)
        n = self.db.butce_kopyala(6, 2026, 7, 2026)
        self.assertEqual(n, 2)
        temmuz = dict(self.db.butce_listele(7, 2026))
        self.assertEqual(temmuz["Market"], 3000.0)
        self.assertEqual(temmuz["Kira"], 8000.0)

    def test_butce_sil(self):
        """Bütçe kategorisi silinebilmeli (#37)."""
        self.db.kaydet_butce(7, 2026, "Market", 3000)
        self.db.kaydet_butce(7, 2026, "Kira", 8000)
        self.db.butce_sil(7, 2026, "Market")
        kalan = dict(self.db.butce_listele(7, 2026))
        self.assertNotIn("Market", kalan)
        self.assertIn("Kira", kalan)

    def test_import_atlanan_raporu(self):
        """İçe aktarmada atlanan satır sayısı raporlanmalı (#40)."""
        import csv as csv_mod
        csv_yol = Path(self.temp_dir.name) / "karisik.csv"
        with open(csv_yol, "w", newline="", encoding="utf-8") as f:
            w = csv_mod.writer(f)
            w.writerow(["tarih", "tur", "kategori", "aciklama", "tutar"])
            w.writerow(["01.07.2026", "Gelir", "Maaş", "ok", "5000"])
            w.writerow(["", "Geçersiz", "", "", ""])  # atlanmalı
            w.writerow(["hatalitar", "Gider", "X", "", "100"])  # tarih hatası
        eklenen = self.db.import_csv(str(csv_yol))
        self.assertEqual(eklenen, 1)
        self.assertEqual(self.db.son_ice_aktarim_atlanan, 2)

    def test_gunluk_haftalik(self):
        """Günlük ve haftalık filtre testi."""
        from datetime import date
        bugun = date.today().strftime("%d.%m.%Y")
        self.db.gelir_ekle(bugun, "Maaş", "Bugün", 1000)

        gunluk = self.db.gunluk_islemler()
        self.assertGreaterEqual(len(gunluk), 1)

        haftalik = self.db.haftalik_islemler()
        self.assertGreaterEqual(len(haftalik), 1)

    def test_aylik_karsilastirma(self):
        """Aylık karşılaştırma testi."""
        self.db.gelir_ekle("05.07.2026", "Maaş", "Test", 5000)
        kars = self.db.aylik_karsilastirma()
        self.assertIn("bu_ay", kars)
        self.assertIn("gecen_ay", kars)
        self.assertGreaterEqual(kars["bu_ay"]["gelir"], 5000.0)

    def test_yillik_karsilastirma(self):
        """Yıllık karşılaştırma testi."""
        self.db.gelir_ekle("05.07.2025", "Maaş", "Test", 3000)
        self.db.gider_ekle("10.07.2025", "Kira", "Test", 1000)
        self.db.gelir_ekle("05.07.2026", "Maaş", "Test", 4000)
        veri = self.db.yillik_karsilastirma()
        veri_dict = {yil: (gelir, gider) for yil, gelir, gider in veri}
        self.assertIn("2025", veri_dict)
        self.assertIn("2026", veri_dict)
        self.assertEqual(veri_dict["2025"], (3000.0, 1000.0))
        self.assertEqual(veri_dict["2026"][0], 4000.0)


if __name__ == "__main__":
    unittest.main()
