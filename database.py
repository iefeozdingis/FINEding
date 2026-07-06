import csv
import shutil
import sqlite3
from pathlib import Path

# ==========================
# Veritabanı Ayarları
# ==========================

DB_FOLDER = Path("database")
DB_FOLDER.mkdir(exist_ok=True)

DB_PATH = DB_FOLDER / "finans.db"


class Database:

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self.create_tables()

    # ==========================
    # Tablolar
    # ==========================

    def create_tables(self):

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS islemler(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            tarih TEXT NOT NULL,

            tur TEXT NOT NULL,

            kategori TEXT NOT NULL,

            aciklama TEXT,

            tutar REAL NOT NULL

        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS butceler(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ay INTEGER NOT NULL,
            yil INTEGER NOT NULL,
            kategori TEXT NOT NULL,
            tutar REAL NOT NULL,
            UNIQUE(ay, yil, kategori)
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS ayarlar(
            anahtar TEXT PRIMARY KEY,
            deger TEXT
        )
        """)

        self.conn.commit()

    # ==========================
    # GELİR EKLE
    # ==========================

    def gelir_ekle(self, tarih, kategori, aciklama, tutar):

        self.cursor.execute("""
        INSERT INTO islemler
        (tarih,tur,kategori,aciklama,tutar)

        VALUES (?,?,?,?,?)

        """, (
            tarih,
            "Gelir",
            kategori,
            aciklama,
            tutar
        ))

        self.conn.commit()

    # ==========================
    # GİDER EKLE
    # ==========================

    def gider_ekle(self, tarih, kategori, aciklama, tutar):

        self.cursor.execute("""
        INSERT INTO islemler
        (tarih,tur,kategori,aciklama,tutar)

        VALUES (?,?,?,?,?)

        """, (
            tarih,
            "Gider",
            kategori,
            aciklama,
            tutar
        ))

        self.conn.commit()

    # ==========================
    # TÜM İŞLEMLER
    # ==========================

    def tum_islemler(self):

        self.cursor.execute("""
        SELECT *

        FROM islemler

        ORDER BY id DESC
        """)

        return self.cursor.fetchall()

    def guncelle_islem(self, id, tarih, tur, kategori, aciklama, tutar):
        self.cursor.execute("""
        UPDATE islemler
        SET tarih=?, tur=?, kategori=?, aciklama=?, tutar=?
        WHERE id=?
        """, (tarih, tur, kategori, aciklama, tutar, id))
        self.conn.commit()

    def islemler_aralik(self, baslangic, bitis):
        self.cursor.execute("""
        SELECT *
        FROM islemler
        WHERE tarih BETWEEN ? AND ?
        ORDER BY id DESC
        """, (baslangic, bitis))
        return self.cursor.fetchall()

    def toplam_gelir_aralik(self, baslangic, bitis):
        self.cursor.execute("""
        SELECT IFNULL(SUM(tutar),0)
        FROM islemler
        WHERE tur='Gelir' AND tarih BETWEEN ? AND ?
        """, (baslangic, bitis))
        return self.cursor.fetchone()[0]

    def toplam_gider_aralik(self, baslangic, bitis):
        self.cursor.execute("""
        SELECT IFNULL(SUM(tutar),0)
        FROM islemler
        WHERE tur='Gider' AND tarih BETWEEN ? AND ?
        """, (baslangic, bitis))
        return self.cursor.fetchone()[0]

    def kategori_toplamlari(self, tur=None):
        sorgu = "SELECT kategori, SUM(tutar) FROM islemler"
        kosullar = []
        if tur:
            sorgu += " WHERE tur=?"
            kosullar.append(tur)
        sorgu += " GROUP BY kategori ORDER BY SUM(tutar) DESC"
        self.cursor.execute(sorgu, tuple(kosullar))
        return self.cursor.fetchall()

    def export_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8") as dosya:
            writer = csv.writer(dosya)
            writer.writerow(["id", "tarih", "tur", "kategori", "aciklama", "tutar"])
            for satir in self.tum_islemler():
                writer.writerow(satir)

    def kaydet_butce(self, ay, yil, kategori, tutar):
        self.cursor.execute("""
        INSERT INTO butceler (ay, yil, kategori, tutar)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(ay, yil, kategori) DO UPDATE SET tutar=excluded.tutar
        """, (ay, yil, kategori, tutar))
        self.conn.commit()

    def butce_listele(self, ay, yil):
        self.cursor.execute("""
        SELECT kategori, tutar FROM butceler
        WHERE ay=? AND yil=?
        ORDER BY kategori
        """, (ay, yil))
        return self.cursor.fetchall()

    def butce_durumu(self, ay, yil):
        self.cursor.execute("""
        SELECT b.kategori, b.tutar AS butce, COALESCE(SUM(CASE WHEN i.tur='Gider' THEN i.tutar ELSE 0 END), 0) AS harcanan
        FROM butceler b
        LEFT JOIN islemler i ON i.kategori = b.kategori
        AND strftime('%m', substr(i.tarih, 7, 4) || '-' || substr(i.tarih, 4, 2) || '-' || substr(i.tarih, 1, 2)) = printf('%02d', b.ay)
        AND strftime('%Y', substr(i.tarih, 7, 4) || '-' || substr(i.tarih, 4, 2) || '-' || substr(i.tarih, 1, 2)) = ?
        WHERE b.ay=? AND b.yil=?
        GROUP BY b.kategori, b.tutar
        ORDER BY b.kategori
        """, (str(yil), ay, yil))
        sonuc = []
        for kategori, butce, harcanan in self.cursor.fetchall():
            sonuc.append({
                "kategori": kategori,
                "butce": float(butce),
                "harcanan": float(harcanan),
                "kalan": float(butce) - float(harcanan),
            })
        return sonuc

    def ayar_kaydet(self, anahtar, deger):
        self.cursor.execute("""
        INSERT INTO ayarlar (anahtar, deger)
        VALUES (?, ?)
        ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger
        """, (anahtar, deger))
        self.conn.commit()

    def yedekle(self, hedef_yol):
        shutil.copy2(DB_PATH, hedef_yol)

    def geri_yukle(self, kaynak_yol):
        shutil.copy2(kaynak_yol, DB_PATH)
        self.conn.close()
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()

    def ayar_oku(self, anahtar, varsayilan=None):
        self.cursor.execute("SELECT deger FROM ayarlar WHERE anahtar=?", (anahtar,))
        sonuc = self.cursor.fetchone()
        return sonuc[0] if sonuc else varsayilan

    # ==========================
    # TOPLAM GELİR
    # ==========================

    def toplam_gelir(self):

        self.cursor.execute("""
        SELECT IFNULL(SUM(tutar),0)

        FROM islemler

        WHERE tur='Gelir'
        """)

        return self.cursor.fetchone()[0]

    # ==========================
    # TOPLAM GİDER
    # ==========================

    def toplam_gider(self):

        self.cursor.execute("""
        SELECT IFNULL(SUM(tutar),0)

        FROM islemler

        WHERE tur='Gider'
        """)

        return self.cursor.fetchone()[0]

    # ==========================
    # BAKİYE
    # ==========================

    def bakiye(self):

        return self.toplam_gelir() - self.toplam_gider()

    # ==========================
    # İŞLEM SİL
    # ==========================

    def sil(self, id):

        self.cursor.execute(
            "DELETE FROM islemler WHERE id=?",
            (id,)
        )

        self.conn.commit()

    # ==========================
    # KAPAT
    # ==========================

    def close(self):

        self.conn.close()