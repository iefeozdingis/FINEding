"""para_parse / para_formatla birim testleri — Tk gerektirmez."""

import unittest

from ui.money import para_formatla, para_parse


class TestParaParse(unittest.TestCase):
    def test_sade_tam_sayi(self):
        self.assertEqual(para_parse("1500"), 1500.0)

    def test_nokta_ondalik_kucuk(self):
        # "12.5" binlik değil ondalık olmalı (10x hata düzeltmesi)
        self.assertEqual(para_parse("12.5"), 12.5)

    def test_nokta_ondalik_iki_hane(self):
        self.assertEqual(para_parse("1500.50"), 1500.50)

    def test_virgul_ondalik(self):
        self.assertEqual(para_parse("12,5"), 12.5)

    def test_turk_format(self):
        self.assertEqual(para_parse("1.234,56"), 1234.56)

    def test_turk_format_buyuk(self):
        self.assertEqual(para_parse("1.500.000,00"), 1500000.0)

    def test_abd_format(self):
        self.assertEqual(para_parse("1,234.56"), 1234.56)

    def test_binlik_nokta_ondalik_yok(self):
        # "1.500" → 1500 (binlik ayraç), 1.5 değil
        self.assertEqual(para_parse("1.500"), 1500.0)

    def test_binlik_virgul_ondalik_yok(self):
        self.assertEqual(para_parse("1,500"), 1500.0)

    def test_negatif(self):
        self.assertEqual(para_parse("-1.234,56"), -1234.56)

    def test_sembol_ve_bosluk(self):
        self.assertEqual(para_parse("1.234,56 ₺"), 1234.56)

    def test_gecersiz(self):
        for kotu in ("", "abc", "12.34.56,78,9", "1.2.3,4,5", "12,3.4,5"):
            with self.assertRaises(ValueError):
                para_parse(kotu)


class TestParaFormatla(unittest.TestCase):
    def test_temel(self):
        self.assertEqual(para_formatla(1234.56), "1.234,56 ₺")

    def test_negatif(self):
        self.assertEqual(para_formatla(-1234.56), "-1.234,56 ₺")

    def test_sembolsuz(self):
        self.assertEqual(para_formatla(1234.56, sembol=False), "1.234,56")

    def test_ondalik_sifir(self):
        self.assertEqual(para_formatla(1500, ondalik=0), "1.500 ₺")

    def test_roundtrip(self):
        # format → parse → aynı değer
        for deger in (0.0, 12.5, 1234.56, 1500000.0, -99.99):
            self.assertAlmostEqual(
                para_parse(para_formatla(deger, sembol=False)), deger, places=2
            )


if __name__ == "__main__":
    unittest.main()
