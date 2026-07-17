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
        """Borç ödemesi kalanı düşürüp gider işlemi üretmeli (#10)."""
        borc_id = self.db.borc_ekle(
            "Borç", "Kredi Kartı", "Banka", 10000, 10000, "01.06.2026", "01.12.2026"
        )
        self.db.borc_odeme_yap(borc_id, 3000, "15.07.2026")

        borc = self.db.borclari_listele("Aktif")[0]
        self.assertEqual(borc["kalan_tutar"], 7000.0)
        gider = self.db.islem_ara("ödemesi", "Gider")
        self.assertEqual(len(gider), 1)
        self.assertEqual(gider[0][5], 3000.0)
        gecmis = self.db.borc_odemeleri(borc_id)
        self.assertEqual(len(gecmis), 1)

        # Tam ödeme → Ödendi
        self.db.borc_odeme_yap(borc_id, 7000, "20.07.2026")
        self.assertEqual(len(self.db.borclari_listele("Ödendi")), 1)

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
