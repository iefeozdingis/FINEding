import unittest

try:
    import tkinter as tk
    _TK_VAR = True
except ImportError:
    _TK_VAR = False


class FakeEvent:
    def __init__(self, widget, keysym):
        self.widget = widget
        self.keysym = keysym


def _tarih_yaz(entry, metin):
    """Bir Entry'ye karakter karakter yazarak gerçek kullanıcı girdisini simüle eder."""
    from ui.utils import tarih_formatla
    for karakter in metin:
        pos = entry.index("insert")
        entry.insert(pos, karakter)
        entry.icursor(pos + 1)
        tarih_formatla(FakeEvent(entry, karakter))


@unittest.skipUnless(_TK_VAR, "tkinter kurulu değil")
class TestTarihFormatla(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
        except tk.TclError as e:
            # Ekran/DISPLAY yoksa (xvfb'siz headless) testi atla, hata verme
            raise unittest.SkipTest(f"Tk başlatılamadı: {e}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_bos_alana_tarih_yazma(self):
        entry = tk.Entry(self.root)
        _tarih_yaz(entry, "13072026")
        self.assertEqual(entry.get(), "13.07.2026")

    def test_gun_ay_sifirla_baslayan_tarih(self):
        entry = tk.Entry(self.root)
        _tarih_yaz(entry, "01012025")
        self.assertEqual(entry.get(), "01.01.2025")

    def test_onceden_dolu_alanda_yil_duzenleme(self):
        entry = tk.Entry(self.root)
        entry.insert(0, "13.07.2026")
        entry.icursor(10)
        for _ in range(4):
            pos = entry.index("insert")
            entry.delete(pos - 1, pos)
            entry.icursor(pos - 1)
        _tarih_yaz(entry, "2027")
        self.assertEqual(entry.get(), "13.07.2027")


if __name__ == "__main__":
    unittest.main()
