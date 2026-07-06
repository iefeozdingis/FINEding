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
        self.assertEqual(islem[1], "02.01.2026")
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


if __name__ == "__main__":
    unittest.main()
