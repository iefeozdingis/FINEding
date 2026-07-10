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
        self.assertTrue(self.db.kullanici_kaydet("admin", "admin", "Yönetici"))
        kullanici = self.db.kullanici_dogrula("admin", "admin")
        self.assertIsNotNone(kullanici)
        assert kullanici is not None
        self.assertEqual(kullanici["kullanici_adi"], "admin")
        # İlk kullanıcı admin olmalı
        self.assertTrue(self.db.kullanici_admin_mi(kullanici["id"]))

        # Yanlış şifre
        self.assertIsNone(self.db.kullanici_dogrula("admin", "yanlis"))

        # Yeni kullanıcı
        self.assertTrue(self.db.kullanici_kaydet("test", "12345", "Test Kullanıcı"))
        self.assertFalse(self.db.kullanici_kaydet("test", "12345", "Dup"))

        k = self.db.kullanici_dogrula("test", "12345")
        self.assertIsNotNone(k)
        assert k is not None
        self.assertEqual(k["ad_soyad"], "Test Kullanıcı")

        # Şifre değiştir
        self.db.kullanici_sifre_degistir(k["id"], "yenisifre")
        self.assertIsNone(self.db.kullanici_dogrula("test", "12345"))
        self.assertIsNotNone(self.db.kullanici_dogrula("test", "yenisifre"))

        # Admin kendini silemez
        self.assertFalse(self.db.kullanici_sil(1))
        # Normal kullanıcı silinebilir
        self.assertTrue(self.db.kullanici_sil(k["id"]))

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

    def test_bcrypt_hash(self):
        """Bcrypt hash'leme ve doğrulama testi."""
        from database import _sifre_hashla, _sifre_dogrula
        sifre = "test123"
        hash_deger = _sifre_hashla(sifre)
        self.assertTrue(hash_deger.startswith("$2b$") or len(hash_deger) == 64)
        self.assertTrue(_sifre_dogrula(sifre, hash_deger))
        self.assertFalse(_sifre_dogrula("yanlis", hash_deger))

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
