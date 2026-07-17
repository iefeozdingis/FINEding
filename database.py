import csv
import hashlib
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ==========================
# Veritabanı Ayarları
# ==========================

DB_FOLDER = Path("database")
DB_FOLDER.mkdir(exist_ok=True)

DB_PATH = DB_FOLDER / "finans.db"

# Güvenli şifre hash'leme

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False


def _sifre_hashla(sifre: str) -> str:
    """bcrypt ile şifre hash'ler, yoksa SHA-256'ya düşer."""
    if _HAS_BCRYPT:
        return bcrypt.hashpw(sifre.encode(), bcrypt.gensalt()).decode()
    return hashlib.sha256(b"Fineding2024!" + sifre.encode()).hexdigest()


def _sifre_dogrula(sifre: str, hash_deger: str) -> bool:
    """Şifre ile hash'i karşılaştırır (bcrypt veya eski SHA-256 hash'ler için)."""
    if hash_deger.startswith("$2"):
        if _HAS_BCRYPT:
            return bcrypt.checkpw(sifre.encode(), hash_deger.encode())
        return False
    # Eski (bcrypt öncesi) SHA-256 hash — _sifre_hashla burada kullanılamaz,
    # bcrypt mevcutken her zaman yeni bir bcrypt hash üretir ve asla eşleşmez.
    legacy_hash = hashlib.sha256(b"Fineding2024!" + sifre.encode()).hexdigest()
    return legacy_hash == hash_deger


def para_yuvarla(tutar: Any) -> float:
    """Tutarı 2 ondalık haneye yuvarlar (kuruş).

    Para REAL (float) saklandığı için 0.1+0.2 sınıfı birikimli yuvarlama
    hataları oluşabiliyor; tüm yazma noktalarında bilinçli yuvarlama
    uygulanarak bakiye/bütçe karşılaştırmaları tutarlı tutulur.
    """
    return round(float(tutar), 2)


def normalize_date(tarih_str: str) -> str:
    """Normalize a date string to ISO YYYY-MM-DD.

    Accepts DD.MM.YYYY or YYYY-MM-DD and returns YYYY-MM-DD.
    Raises ValueError on invalid formats.
    """
    if not isinstance(tarih_str, str):
        raise ValueError("Tarih string olmalidir")

    tarih_str = tarih_str.strip()
    # DD.MM.YYYY
    try:
        if "." in tarih_str:
            dt = datetime.strptime(tarih_str, "%d.%m.%Y")
            return dt.strftime("%Y-%m-%d")
        # YYYY-MM-DD
        dt = datetime.strptime(tarih_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        raise ValueError(f"Geçersiz tarih formatı: {tarih_str}") from e


# Şema sürümü — her artışta _migrate() ilgili adımı uygular
SCHEMA_VERSION = 1


class Database:
    def __init__(self) -> None:
        self.conn = self._baglan()
        self.cursor = self.conn.cursor()
        self._son_silinen: Optional[Tuple[Any, ...]] = None
        self.create_tables()
        self._migrate()
        self._index_olustur()

    @staticmethod
    def _baglan() -> sqlite3.Connection:
        """Ortak bağlantı ayarlarıyla SQLite bağlantısı açar.

        busy_timeout: arka plan thread'leri (tekrarlayan/borç kontrolü) ve UI
        aynı anda yazınca 'database is locked' hatası yerine kısa süre bekler.
        """
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _migrate(self) -> None:
        """PRAGMA user_version tabanlı numaralı şema migrasyonu.

        'dene-yut' ALTER TABLE yerine sürüm numarasıyla ilerleyen, gerçek
        hataları yutmayan bir yol. Mevcut normalize edilmemiş borç
        tarihlerini de ISO'ya çevirir.
        """
        mevcut = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if mevcut < 1:
            self._migrate_borc_tarihleri()
            self.conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            self.conn.commit()

    def _migrate_borc_tarihleri(self) -> None:
        """Eski GG.AA.YYYY borç tarihlerini ISO YYYY-MM-DD'ye çevirir."""
        self.cursor.execute(
            "SELECT id, baslangic_tarih, vade_tarih FROM borclar"
        )
        for bid, bas, vade in self.cursor.fetchall():
            yeni_bas = self._iso_veya_ayni(bas)
            yeni_vade = self._iso_veya_ayni(vade)
            if yeni_bas != bas or yeni_vade != vade:
                self.conn.execute(
                    "UPDATE borclar SET baslangic_tarih=?, vade_tarih=? WHERE id=?",
                    (yeni_bas, yeni_vade, bid),
                )

    @staticmethod
    def _iso_veya_ayni(tarih: Any) -> Any:
        """GG.AA.YYYY ise ISO'ya çevirir, aksi halde olduğu gibi bırakır."""
        if not tarih or not isinstance(tarih, str) or "." not in tarih:
            return tarih
        try:
            return normalize_date(tarih)
        except ValueError:
            return tarih

    def _index_olustur(self) -> None:
        """Sık kullanılan filtre kolonlarına index ekler (yoksa)."""
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_islemler_tarih ON islemler(tarih)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_islemler_tur_tarih "
            "ON islemler(tur, tarih)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_islemler_kategori "
            "ON islemler(kategori)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_borclar_vade "
            "ON borclar(durum, vade_tarih)"
        )
        self.conn.commit()

    # ==========================
    # Tablolar
    # ==========================

    def create_tables(self) -> None:
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
        # Etiket sütunu (önceden yoksa ekle)
        try:
            self.cursor.execute("ALTER TABLE islemler ADD COLUMN etiketler TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # Zaten varsa geç

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

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS planlanan(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ay INTEGER NOT NULL,
            yil INTEGER NOT NULL,
            kategori TEXT NOT NULL,
            tur TEXT NOT NULL,
            aciklama TEXT,
            tutar REAL NOT NULL
        )
        """)
        # Aktarım tarihi (mükerrer aktarımı önlemek için, önceden yoksa ekle)
        try:
            self.cursor.execute(
                "ALTER TABLE planlanan ADD COLUMN aktarim_tarihi TEXT DEFAULT ''"
            )
        except sqlite3.OperationalError:
            pass

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS borclar(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tur TEXT NOT NULL,
            aciklama TEXT NOT NULL,
            kisi TEXT,
            toplam_tutar REAL NOT NULL,
            kalan_tutar REAL NOT NULL,
            baslangic_tarih TEXT,
            vade_tarih TEXT,
            durum TEXT NOT NULL DEFAULT 'Aktif'
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS kullanicilar(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_adi TEXT UNIQUE NOT NULL,
            sifre_hash TEXT NOT NULL,
            ad_soyad TEXT,
            olusturma_tarihi TEXT NOT NULL
        )
        """)

        # Tekrarlayan işlemler
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS tekrarlayan(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tur TEXT NOT NULL,
            kategori TEXT NOT NULL,
            aciklama TEXT,
            tutar REAL NOT NULL,
            gun INTEGER NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1
        )
        """)

        # İşlem geçmişi (audit log)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS islem_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zaman TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            islem_turu TEXT NOT NULL,
            islem_id INTEGER,
            detay TEXT
        )
        """)

        # Borç/alacak ödeme geçmişi
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS borc_odemeler(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            borc_id INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            tutar REAL NOT NULL
        )
        """)

        # Tasarruf hedefleri
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasarruf_hedefleri(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT NOT NULL,
            hedef_tutar REAL NOT NULL,
            biriken_tutar REAL NOT NULL DEFAULT 0,
            hedef_tarih TEXT
        )
        """)

        # İlk kullanıcı otomatik admin olur (ID=1)

        self.conn.commit()

    # ==========================
    # İŞLEM LOG KAYDI
    # ==========================

    def _log_islem(self, islem_turu: str, islem_id: Any = None, detay: str = "") -> None:
        """İşlemi audit log'a yazar (commit ETMEZ — çağıranın transaction'ına
        dahildir; böylece kayıt + log atomik olur)."""
        self.cursor.execute(
            "INSERT INTO islem_log (islem_turu, islem_id, detay) VALUES (?,?,?)",
            (islem_turu, islem_id, detay),
        )

    # ==========================
    # GELİR EKLE
    # ==========================

    def gelir_ekle(
        self, tarih: str, kategori: str, aciklama: Optional[str], tutar: float,
        etiketler: str = ""
    ) -> None:
        tarih_iso = normalize_date(tarih)
        self.cursor.execute(
            """
        INSERT INTO islemler
        (tarih,tur,kategori,aciklama,tutar,etiketler)

        VALUES (?,?,?,?,?,?)

        """,
            (tarih_iso, "Gelir", kategori, aciklama, para_yuvarla(tutar), etiketler),
        )
        self._log_islem("gelir_ekle", self.cursor.lastrowid, f"{kategori}: {tutar}")
        self.conn.commit()

    # ==========================
    # GİDER EKLE
    # ==========================

    def gider_ekle(
        self, tarih: str, kategori: str, aciklama: Optional[str], tutar: float,
        etiketler: str = ""
    ) -> None:
        tarih_iso = normalize_date(tarih)
        self.cursor.execute(
            """
        INSERT INTO islemler
        (tarih,tur,kategori,aciklama,tutar,etiketler)

        VALUES (?,?,?,?,?,?)

        """,
            (tarih_iso, "Gider", kategori, aciklama, para_yuvarla(tutar), etiketler),
        )
        self._log_islem("gider_ekle", self.cursor.lastrowid, f"{kategori}: {tutar}")
        self.conn.commit()

    # ==========================
    # TÜM İŞLEMLER
    # ==========================

    def tum_islemler(self) -> List[Tuple[Any, ...]]:
        self.cursor.execute("""
        SELECT *

        FROM islemler

        ORDER BY id DESC
        """)

        return self.cursor.fetchall()

    def tum_islem_sayisi(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM islemler")
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def islem_ara(self, arama: str = "", tur: str = "") -> List[Tuple[Any, ...]]:
        """Belirtilen metin ve türe göre işlemleri filtreleyerek arar."""
        sorgu = "SELECT * FROM islemler WHERE 1=1"
        params: List[Any] = []
        if arama:
            sorgu += (
                " AND (kategori LIKE ? ESCAPE '\\' OR aciklama LIKE ? ESCAPE '\\'"
                " OR CAST(tutar AS TEXT) LIKE ? ESCAPE '\\'"
                " OR etiketler LIKE ? ESCAPE '\\')"
            )
            # Kullanıcının yazdığı % ve _ joker karakter olarak yorumlanmasın
            kacisli = arama.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            like = f"%{kacisli}%"
            params.extend([like, like, like, like])
        if tur:
            sorgu += " AND tur=?"
            params.append(tur)
        sorgu += " ORDER BY id DESC"
        self.cursor.execute(sorgu, tuple(params))
        return self.cursor.fetchall()

    def guncelle_islem(
        self,
        id: int,
        tarih: str,
        tur: str,
        kategori: str,
        aciklama: Optional[str],
        tutar: float,
        etiketler: Optional[str] = None,
    ) -> None:
        tarih_iso = normalize_date(tarih)
        tutar = para_yuvarla(tutar)
        if etiketler is None:
            self.cursor.execute(
                """
            UPDATE islemler
            SET tarih=?, tur=?, kategori=?, aciklama=?, tutar=?
            WHERE id=?
            """,
                (tarih_iso, tur, kategori, aciklama, tutar, id),
            )
        else:
            self.cursor.execute(
                """
            UPDATE islemler
            SET tarih=?, tur=?, kategori=?, aciklama=?, tutar=?, etiketler=?
            WHERE id=?
            """,
                (tarih_iso, tur, kategori, aciklama, tutar, etiketler, id),
            )
        self._log_islem("guncelle", id, f"{kategori}: {tutar}")
        self.conn.commit()

    def islemler_aralik(self, baslangic: str, bitis: str) -> List[Tuple[Any, ...]]:
        bas_iso = normalize_date(baslangic)
        bit_iso = normalize_date(bitis)
        self.cursor.execute(
            """
        SELECT *
        FROM islemler
        WHERE tarih BETWEEN ? AND ?
        ORDER BY id DESC
        """,
            (bas_iso, bit_iso),
        )
        return self.cursor.fetchall()

    def toplam_gelir_aralik(self, baslangic: str, bitis: str) -> float:
        bas_iso = normalize_date(baslangic)
        bit_iso = normalize_date(bitis)
        self.cursor.execute(
            """
        SELECT IFNULL(SUM(tutar),0)
        FROM islemler
        WHERE tur='Gelir' AND tarih BETWEEN ? AND ?
        """,
            (bas_iso, bit_iso),
        )
        row = self.cursor.fetchone()
        val = row[0] if row and row[0] is not None else 0.0
        return float(val)

    def toplam_gider_aralik(self, baslangic: str, bitis: str) -> float:
        bas_iso = normalize_date(baslangic)
        bit_iso = normalize_date(bitis)
        self.cursor.execute(
            """
        SELECT IFNULL(SUM(tutar),0)
        FROM islemler
        WHERE tur='Gider' AND tarih BETWEEN ? AND ?
        """,
            (bas_iso, bit_iso),
        )
        row = self.cursor.fetchone()
        val = row[0] if row and row[0] is not None else 0.0
        return float(val)

    def kategori_toplamlari(self, tur: Optional[str] = None) -> List[Tuple[str, float]]:
        sorgu = "SELECT kategori, SUM(tutar) FROM islemler"
        kosullar = []
        if tur:
            sorgu += " WHERE tur=?"
            kosullar.append(tur)
        sorgu += " GROUP BY kategori ORDER BY SUM(tutar) DESC"
        if kosullar:
            self.cursor.execute(sorgu, tuple(kosullar))
        else:
            self.cursor.execute(sorgu)
        return self.cursor.fetchall()

    def aylik_ozet(self) -> List[Tuple[str, float, float]]:
        """(ay, gelir_toplam, gider_toplam) listesi döner. Son 12 ay."""
        self.cursor.execute("""
        SELECT
            strftime('%Y-%m', tarih) AS ay,
            SUM(CASE WHEN tur='Gelir' THEN tutar ELSE 0 END),
            SUM(CASE WHEN tur='Gider' THEN tutar ELSE 0 END)
        FROM islemler
        GROUP BY ay
        ORDER BY ay DESC
        LIMIT 12
        """)
        return [(r[0], float(r[1]), float(r[2])) for r in self.cursor.fetchall()]

    def export_csv(self, path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as dosya:
            writer = csv.writer(dosya)
            writer.writerow(["id", "tarih", "tur", "kategori", "aciklama", "tutar"])
            for satir in self.tum_islemler():
                # Tarihi GG.AA.YYYY formatına çevir
                try:
                    dt = datetime.strptime(satir[1], "%Y-%m-%d")
                    tarih_goster = dt.strftime("%d.%m.%Y")
                except ValueError:
                    tarih_goster = satir[1]
                writer.writerow(
                    [satir[0], tarih_goster, satir[2], satir[3], satir[4], satir[5]]
                )

    def import_csv(self, path: str) -> int:
        """CSV dosyasından işlemleri içe aktarır. Eklenen satır sayısını döner."""
        eklenen = 0
        with open(path, "r", encoding="utf-8-sig") as dosya:
            reader = csv.DictReader(dosya)
            for satir in reader:
                try:
                    eklenen += self._satir_ekle_guvenli(satir)
                except (ValueError, KeyError):
                    continue
        self.conn.commit()
        return eklenen

    def import_excel(self, path: str) -> int:
        """Excel (.xlsx) dosyasından işlemleri içe aktarır. Eklenen satır sayısını döner."""
        from openpyxl import load_workbook

        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb.active
            satirlar = ws.iter_rows(values_only=True)
            try:
                baslik = [str(h).strip().lower() if h else "" for h in next(satirlar)]
            except StopIteration:
                return 0

            # Türkçe/İngilizce başlık eşlemesi (ID/Tarih/Tür/Kategori/Açıklama/Tutar/Etiket)
            eslesme = {
                "tarih": "tarih", "date": "tarih",
                "tür": "tur", "tur": "tur", "type": "tur",
                "kategori": "kategori", "category": "kategori",
                "açıklama": "aciklama", "aciklama": "aciklama", "description": "aciklama",
                "tutar": "tutar", "amount": "tutar",
                "etiket": "etiketler", "etiketler": "etiketler", "tags": "etiketler",
            }
            indeksler = {}
            for i, h in enumerate(baslik):
                if h in eslesme:
                    indeksler[eslesme[h]] = i

            eklenen = 0
            for row in satirlar:
                if row is None or all(v is None for v in row):
                    continue
                try:
                    satir = {
                        "tarih": row[indeksler["tarih"]] if "tarih" in indeksler else "",
                        "tur": row[indeksler["tur"]] if "tur" in indeksler else "",
                        "kategori": row[indeksler["kategori"]] if "kategori" in indeksler else "",
                        "aciklama": row[indeksler["aciklama"]] if "aciklama" in indeksler else "",
                        "tutar": row[indeksler["tutar"]] if "tutar" in indeksler else 0,
                        "etiketler": row[indeksler["etiketler"]] if "etiketler" in indeksler else "",
                    }
                    eklenen += self._satir_ekle_guvenli(
                        {k: ("" if v is None else str(v)) for k, v in satir.items()}
                    )
                except (ValueError, KeyError):
                    continue
            self.conn.commit()
            return eklenen
        finally:
            wb.close()

    @staticmethod
    def _tutar_parse(ham: Any) -> float:
        """İçe aktarımda tutarı hem sade hem Türk (1.234,56) formatından okur."""
        if ham is None:
            return 0.0
        s = str(ham).strip().replace("₺", "").replace(" ", "")
        if not s:
            return 0.0
        # datetime hücresi vb. sayı olmayan değerleri reddet
        if any(c not in "0123456789.,-" for c in s):
            raise ValueError(f"Geçersiz tutar: {ham!r}")
        son_nokta = s.rfind(".")
        son_virgul = s.rfind(",")
        if son_nokta != -1 and son_virgul != -1:
            ondalik = "." if son_nokta > son_virgul else ","
            binlik = "," if ondalik == "." else "."
            s = s.replace(binlik, "").replace(ondalik, ".")
        elif son_virgul != -1:
            # Türk formatı: virgül ondalık ayracı
            if s.count(",") == 1 and len(s) - son_virgul - 1 in (1, 2):
                s = s.replace(",", ".")
            else:
                s = s.replace(",", "")
        return float(s)

    def _satir_ekle_guvenli(self, satir: Dict[str, str]) -> int:
        """CSV/Excel içe aktarımı için ortak satır doğrulama ve ekleme mantığı (commit çağırmaz)."""
        tarih = normalize_date(satir.get("tarih", ""))
        tur = satir.get("tur", "").strip()
        kategori = satir.get("kategori", "").strip()
        aciklama = satir.get("aciklama", "").strip() or None
        tutar = para_yuvarla(self._tutar_parse(satir.get("tutar", "0")))
        etiketler = satir.get("etiketler", "").strip()
        if tur not in ("Gelir", "Gider") or not kategori:
            return 0
        self.cursor.execute(
            "INSERT INTO islemler (tarih, tur, kategori, aciklama, tutar, etiketler) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tarih, tur, kategori, aciklama, tutar, etiketler),
        )
        return 1

    def kaydet_butce(self, ay: int, yil: int, kategori: str, tutar: float) -> None:
        self.cursor.execute(
            """
        INSERT INTO butceler (ay, yil, kategori, tutar)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(ay, yil, kategori) DO UPDATE SET tutar=excluded.tutar
        """,
            (ay, yil, kategori, para_yuvarla(tutar)),
        )
        self.conn.commit()

    def butce_listele(self, ay: int, yil: int) -> List[Tuple[str, float]]:
        self.cursor.execute(
            """
        SELECT kategori, tutar FROM butceler
        WHERE ay=? AND yil=?
        ORDER BY kategori
        """,
            (ay, yil),
        )
        return self.cursor.fetchall()

    def butce_durumu(self, ay: int, yil: int) -> List[Dict[str, Any]]:
        self.cursor.execute(
            """
        SELECT
            b.kategori,
            b.tutar AS butce,
            COALESCE(
                SUM(CASE WHEN i.tur='Gider' THEN i.tutar ELSE 0 END),
                0
            ) AS harcanan
        FROM butceler b
        LEFT JOIN islemler i ON i.kategori = b.kategori
        AND strftime('%m', i.tarih) = printf('%02d', b.ay)
        AND strftime('%Y', i.tarih) = b.yil
        WHERE b.ay=? AND b.yil=?
        GROUP BY b.kategori, b.tutar
        ORDER BY b.kategori
        """,
            (ay, yil),
        )
        sonuc = []
        for kategori, butce, harcanan in self.cursor.fetchall():
            sonuc.append(
                {
                    "kategori": kategori,
                    "butce": float(butce),
                    "harcanan": float(harcanan),
                    "kalan": float(butce) - float(harcanan),
                }
            )
        return sonuc

    def ayar_kaydet(self, anahtar: str, deger: str) -> None:
        self.cursor.execute(
            """
        INSERT INTO ayarlar (anahtar, deger)
        VALUES (?, ?)
        ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger
        """,
            (anahtar, deger),
        )
        self.conn.commit()

    def yedekle(self, hedef_yol: str) -> None:
        # WAL modunda veriler önce -wal dosyasına yazılır; checkpoint
        # yapılmadan ana .db dosyası kopyalanırsa yedek eksik/boş çıkar.
        # Ayrı/geçici bir cursor kullanılır: self.cursor üzerinden checkpoint
        # çağırmak Windows'ta ana .db dosyasını sonradan kilitli bırakıyor.
        self.conn.commit()
        gecici_cursor = self.conn.cursor()
        gecici_cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        gecici_cursor.close()
        shutil.copy2(DB_PATH, hedef_yol)
        # create checksum file next to backup
        h = hashlib.sha256()
        with open(hedef_yol, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        checksum_path = str(hedef_yol) + ".sha256"
        with open(checksum_path, "w", encoding="utf-8") as cf:
            cf.write(h.hexdigest())

    def geri_yukle(self, kaynak_yol: str) -> None:
        # Bütünlük kontrolü (varsa)
        checksum_path = str(kaynak_yol) + ".sha256"
        if Path(checksum_path).exists():
            h = hashlib.sha256()
            with open(kaynak_yol, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            with open(checksum_path, "r", encoding="utf-8") as cf:
                expected = cf.read().strip()
            if h.hexdigest() != expected:
                raise ValueError("Yedek bütünlük kontrolü başarısız.")

        # Dosyanın gerçekten bir SQLite veritabanı olduğunu doğrula —
        # bozuk/yabancı bir dosya tüm veriyi (kullanıcı tablosu dahil) yok eder.
        with open(kaynak_yol, "rb") as f:
            if f.read(16) != b"SQLite format 3\x00":
                raise ValueError("Seçilen dosya geçerli bir yedek değil.")
        gecici = sqlite3.connect(kaynak_yol)
        try:
            if gecici.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Yedek dosyası bozuk (integrity_check).")
        finally:
            gecici.close()

        # Mevcut veritabanını üzerine yazmadan önce güvenlik yedeği al
        try:
            self.conn.commit()
            self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        self.conn.close()

        # Eski WAL/SHM dosyaları geri yüklenen DB'nin üzerine 'replay'
        # edilip sessiz bozulmaya yol açabilir — kopyalamadan önce silinir.
        for ek in ("-wal", "-shm"):
            yan = Path(str(DB_PATH) + ek)
            if yan.exists():
                try:
                    yan.unlink()
                except OSError:
                    pass
        if Path(DB_PATH).exists():
            try:
                shutil.copy2(DB_PATH, str(DB_PATH) + ".restore-bak")
            except OSError:
                pass

        shutil.copy2(kaynak_yol, DB_PATH)
        self.conn = self._baglan()
        self.cursor = self.conn.cursor()
        self._son_silinen = None

    def ayar_oku(self, anahtar: str, varsayilan: Optional[str] = None) -> Optional[str]:
        self.cursor.execute("SELECT deger FROM ayarlar WHERE anahtar=?", (anahtar,))
        sonuc = self.cursor.fetchone()
        if not sonuc:
            return varsayilan
        value: Any = sonuc[0]
        if value is None:
            return varsayilan
        return str(value)

    # ==========================
    # TOPLAM GELİR
    # ==========================

    def toplam_gelir(self) -> float:
        self.cursor.execute("""
        SELECT IFNULL(SUM(tutar),0)

        FROM islemler

        WHERE tur='Gelir'
        """)

        row = self.cursor.fetchone()
        val = row[0] if row and row[0] is not None else 0.0
        return float(val)

    # ==========================
    # TOPLAM GİDER
    # ==========================

    def toplam_gider(self) -> float:
        self.cursor.execute("""
        SELECT IFNULL(SUM(tutar),0)

        FROM islemler

        WHERE tur='Gider'
        """)

        row = self.cursor.fetchone()
        val = row[0] if row and row[0] is not None else 0.0
        return float(val)

    # ==========================
    # BAKİYE
    # ==========================

    def bakiye(self) -> float:
        return self.toplam_gelir() - self.toplam_gider()

    # ==========================
    # İŞLEM SİL
    # ==========================

    def sil(self, islem_id: int) -> None:
        # Silmeden önce kaydı sakla (geri almak için)
        self.cursor.execute("SELECT * FROM islemler WHERE id=?", (islem_id,))
        self._son_silinen = self.cursor.fetchone()
        self.cursor.execute("DELETE FROM islemler WHERE id=?", (islem_id,))
        self._log_islem("sil", islem_id, "İşlem silindi")
        self.conn.commit()

    def geri_al(self) -> bool:
        """Son silinen işlemi geri getirir. Başarılıysa True döner."""
        if self._son_silinen is None:
            return False
        try:
            self.cursor.execute("BEGIN")
            veri = self._son_silinen
            if len(veri) >= 7:
                self.cursor.execute(
                    "INSERT INTO islemler "
                    "(id, tarih, tur, kategori, aciklama, tutar, etiketler) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    veri[:7],
                )
            else:
                # Eski DB'lerde etiketler sütunu olmayabilir
                self.cursor.execute(
                    "INSERT INTO islemler (id, tarih, tur, kategori, aciklama, tutar) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    veri[:6],
                )
            self.conn.commit()
            self._son_silinen = None
            return True
        except Exception:
            self.conn.rollback()
            return False

    # ==========================
    # PLANLAMA İŞLEMLERİ
    # ==========================

    def planlanan_ekle(
        self, ay: int, yil: int, kategori: str, tur: str, aciklama: str, tutar: float
    ) -> int:
        self.cursor.execute(
            "INSERT INTO planlanan (ay, yil, kategori, tur, aciklama, tutar) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ay, yil, kategori, tur, aciklama, para_yuvarla(tutar)),
        )
        self.conn.commit()
        assert self.cursor.lastrowid is not None
        return self.cursor.lastrowid

    def planlanan_guncelle(
        self, id: int, kategori: str, tur: str, aciklama: str, tutar: float
    ) -> None:
        self.cursor.execute(
            "UPDATE planlanan SET kategori=?, tur=?, aciklama=?, tutar=? " "WHERE id=?",
            (kategori, tur, aciklama, para_yuvarla(tutar), id),
        )
        self.conn.commit()

    def planlanan_sil(self, id: int) -> None:
        self.cursor.execute("DELETE FROM planlanan WHERE id=?", (id,))
        self.conn.commit()

    def planlanan_listele(self, ay: int, yil: int) -> List[Tuple[Any, ...]]:
        self.cursor.execute(
            "SELECT * FROM planlanan WHERE ay=? AND yil=? ORDER BY tur, kategori",
            (ay, yil),
        )
        return self.cursor.fetchall()

    def plani_aktar(self, ay: int, yil: int, tarih: str) -> Dict[str, int]:
        """Aktarılmamış plan kalemlerini gerçek işlemlere çevirir.

        Mükerrer aktarım koruması: aktarim_tarihi dolu kalemler atlanır,
        böylece butona ikinci kez basmak gelir/gideri ikiye katlamaz.
        {'aktarilan': N, 'atlanan': M} döner.
        """
        tarih_iso = normalize_date(tarih)
        self.cursor.execute(
            "SELECT id, kategori, tur, aciklama, tutar, "
            "COALESCE(aktarim_tarihi,'') FROM planlanan WHERE ay=? AND yil=?",
            (ay, yil),
        )
        satirlar = self.cursor.fetchall()
        aktarilan = 0
        atlanan = 0
        bugun = datetime.now().strftime("%Y-%m-%d %H:%M")
        for pid, kategori, tur, aciklama, tutar, aktarim in satirlar:
            if aktarim:
                atlanan += 1
                continue
            islem_tur = "Gelir" if tur == "Gelir" else "Gider"
            self.cursor.execute(
                "INSERT INTO islemler (tarih, tur, kategori, aciklama, tutar, "
                "etiketler) VALUES (?,?,?,?,?,?)",
                (tarih_iso, islem_tur, kategori, aciklama or "",
                 para_yuvarla(tutar), "plan"),
            )
            self.cursor.execute(
                "UPDATE planlanan SET aktarim_tarihi=? WHERE id=?", (bugun, pid)
            )
            aktarilan += 1
        self.conn.commit()
        return {"aktarilan": aktarilan, "atlanan": atlanan}

    def planlanan_ozet(self, ay: int, yil: int) -> Dict[str, float]:
        self.cursor.execute(
            "SELECT tur, SUM(tutar) FROM planlanan WHERE ay=? AND yil=? "
            "GROUP BY tur",
            (ay, yil),
        )
        sonuc = {"Gelir": 0.0, "Gider": 0.0}
        for tur, toplam in self.cursor.fetchall():
            sonuc[tur] = float(toplam)
        return sonuc

    # ==========================
    # BORÇ / ALACAK İŞLEMLERİ
    # ==========================

    def borc_ekle(
        self,
        tur: str,
        aciklama: str,
        kisi: str,
        toplam: float,
        kalan: float,
        baslangic: str,
        vade: str,
    ) -> int:
        # Borç tarihleri normalize EDİLMİYORDU: GG.AA.YYYY string'i üzerinde
        # ORDER BY vade_tarih sözlüksel sıralama yapıyor, vadeler yanlış
        # sıralanıyordu. Diğer tablolar gibi ISO'ya çevriliyor.
        bas_iso = normalize_date(baslangic) if baslangic else ""
        vade_iso = normalize_date(vade) if vade else ""
        self.cursor.execute(
            "INSERT INTO borclar (tur, aciklama, kisi, toplam_tutar, "
            "kalan_tutar, baslangic_tarih, vade_tarih, durum) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'Aktif')",
            (tur, aciklama, kisi, para_yuvarla(toplam), para_yuvarla(kalan),
             bas_iso, vade_iso),
        )
        self.conn.commit()
        assert self.cursor.lastrowid is not None
        return self.cursor.lastrowid

    def borc_guncelle(self, id: int, kalan: float, durum: str) -> None:
        self.cursor.execute(
            "UPDATE borclar SET kalan_tutar=?, durum=? WHERE id=?",
            (para_yuvarla(kalan), durum, id),
        )
        self.conn.commit()

    def borc_odeme_yap(
        self, borc_id: int, odeme_tutar: float, tarih: str,
        islem_olustur: bool = True,
    ) -> None:
        """Borç/alacağa ödeme işler: kalanı düşürür, ödeme geçmişine yazar ve
        (istenirse) gerçek bir gelir/gider işlemi oluşturur.

        Önceden ödeme yalnızca 'kalan tutarı elle düşür' şeklindeydi; para
        bakiyeye hiç yansımıyordu. Artık ödeme atomik olarak: (1) islemler'e
        Borç için Gider / Alacak (tahsilat) için Gelir kaydı, (2) borc_odemeler
        geçmiş satırı, (3) kalan_tutar düşümü + durum güncellemesi yapar.
        """
        odeme = para_yuvarla(odeme_tutar)
        tarih_iso = normalize_date(tarih)
        try:
            self.cursor.execute("BEGIN")
            self.cursor.execute(
                "SELECT tur, aciklama, kalan_tutar FROM borclar WHERE id=?",
                (borc_id,),
            )
            row = self.cursor.fetchone()
            if row is None:
                raise ValueError("Borç kaydı bulunamadı")
            tur, aciklama, kalan = row[0], row[1], float(row[2])
            yeni_kalan = para_yuvarla(max(0.0, kalan - odeme))
            yeni_durum = "Ödendi" if yeni_kalan <= 0 else "Aktif"

            if islem_olustur:
                islem_tur = "Gider" if tur == "Borç" else "Gelir"
                self.cursor.execute(
                    "INSERT INTO islemler (tarih, tur, kategori, aciklama, "
                    "tutar, etiketler) VALUES (?,?,?,?,?,?)",
                    (tarih_iso, islem_tur, "Borç/Alacak",
                     f"{tur} ödemesi: {aciklama}", odeme, "borc-odeme"),
                )
            self.cursor.execute(
                "INSERT INTO borc_odemeler (borc_id, tarih, tutar) "
                "VALUES (?,?,?)",
                (borc_id, tarih_iso, odeme),
            )
            self.cursor.execute(
                "UPDATE borclar SET kalan_tutar=?, durum=? WHERE id=?",
                (yeni_kalan, yeni_durum, borc_id),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def borc_odemeleri(self, borc_id: int) -> List[Dict[str, Any]]:
        """Bir borç/alacağın ödeme geçmişini döner."""
        self.cursor.execute(
            "SELECT id, tarih, tutar FROM borc_odemeler WHERE borc_id=? "
            "ORDER BY tarih",
            (borc_id,),
        )
        return [
            {"id": r[0], "tarih": r[1], "tutar": float(r[2])}
            for r in self.cursor.fetchall()
        ]

    def borc_sil(self, id: int) -> None:
        self.cursor.execute("DELETE FROM borclar WHERE id=?", (id,))
        self.conn.commit()

    def borclari_listele(self, durum: str = "Aktif") -> List[Dict[str, Any]]:
        if durum == "Tümü":
            self.cursor.execute("SELECT * FROM borclar ORDER BY vade_tarih")
        else:
            self.cursor.execute(
                "SELECT * FROM borclar WHERE durum=? ORDER BY vade_tarih",
                (durum,),
            )
        kolonlar = [
            "id",
            "tur",
            "aciklama",
            "kisi",
            "toplam_tutar",
            "kalan_tutar",
            "baslangic_tarih",
            "vade_tarih",
            "durum",
        ]
        return [dict(zip(kolonlar, satir)) for satir in self.cursor.fetchall()]

    def borc_toplam(self, durum: str = "Aktif") -> float:
        self.cursor.execute(
            "SELECT IFNULL(SUM(kalan_tutar), 0) FROM borclar WHERE durum=?",
            (durum,),
        )
        row = self.cursor.fetchone()
        return float(row[0]) if row else 0.0

    # ==========================
    # KULLANICI İŞLEMLERİ
    # ==========================

    def kullanici_dogrula(
        self, kullanici_adi: str, sifre: str
    ) -> Optional[Dict[str, Any]]:
        """Kullanıcı girişi doğrular, başarılıysa kullanıcı bilgilerini döner."""
        self.cursor.execute(
            "SELECT id, kullanici_adi, ad_soyad, sifre_hash FROM kullanicilar "
            "WHERE kullanici_adi=?",
            (kullanici_adi,),
        )
        row = self.cursor.fetchone()
        if row and _sifre_dogrula(sifre, row[3]):
            return {"id": row[0], "kullanici_adi": row[1], "ad_soyad": row[2]}
        return None

    def kullanici_kaydet(self, kullanici_adi: str, sifre: str, ad_soyad: str) -> bool:
        """Yeni kullanıcı kaydeder. Başarılıysa True."""
        from datetime import datetime as dt

        sifre_hash = _sifre_hashla(sifre)
        try:
            self.cursor.execute(
                "INSERT INTO kullanicilar (kullanici_adi, sifre_hash, ad_soyad, "
                "olusturma_tarihi) VALUES (?, ?, ?, ?)",
                (
                    kullanici_adi,
                    sifre_hash,
                    ad_soyad,
                    dt.now().strftime("%Y-%m-%d %H:%M"),
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def kullanici_sifre_degistir(self, kullanici_id: int, yeni_sifre: str) -> None:
        sifre_hash = _sifre_hashla(yeni_sifre)
        self.cursor.execute(
            "UPDATE kullanicilar SET sifre_hash=? WHERE id=?",
            (sifre_hash, kullanici_id),
        )
        self.conn.commit()

    def kullanici_profil_guncelle(self, kullanici_id: int, ad_soyad: str) -> None:
        self.cursor.execute(
            "UPDATE kullanicilar SET ad_soyad=? WHERE id=?",
            (ad_soyad, kullanici_id),
        )
        self.conn.commit()

    def kullanici_ad_oku(self, kullanici_id: int) -> str:
        self.cursor.execute(
            "SELECT ad_soyad FROM kullanicilar WHERE id=?",
            (kullanici_id,),
        )
        row = self.cursor.fetchone()
        return row[0] if row else ""

    def kullanici_listele(self) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, kullanici_adi, ad_soyad, olusturma_tarihi FROM kullanicilar"
        )
        return [
            {
                "id": r[0],
                "kullanici_adi": r[1],
                "ad_soyad": r[2],
                "olusturma_tarihi": r[3],
            }
            for r in self.cursor.fetchall()
        ]

    def kullanici_admin_mi(self, kullanici_id: int) -> bool:
        """ID'si 1 olan kullanıcı admindir."""
        return kullanici_id == 1

    def kullanici_sil(self, kullanici_id: int) -> bool:
        """Kullanıcıyı sil (admin kendini silemez)."""
        if kullanici_id == 1:
            return False
        self.cursor.execute("DELETE FROM kullanicilar WHERE id=?", (kullanici_id,))
        self.conn.commit()
        return True

    # ==========================
    # ÖZEL KATEGORİ YÖNETİMİ
    # ==========================

    def kategori_ekle(self, tur: str, kategori: str) -> None:
        """Belirtilen tür (Gelir/Gider) için özel kategori ekler."""
        anahtar = f"kategoriler_{tur.lower()}"
        mevcut = self.ayar_oku(anahtar, "") or ""
        kategoriler = [k.strip() for k in mevcut.split(",") if k.strip()]
        if kategori not in kategoriler:
            kategoriler.append(kategori)
            self.ayar_kaydet(anahtar, ",".join(kategoriler))

    def kategorileri_getir(self, tur: str) -> List[str]:
        """Belirtilen tür için tüm kategorileri (varsayılan + özel) döner."""
        anahtar = f"kategoriler_{tur.lower()}"
        mevcut = self.ayar_oku(anahtar, "") or ""
        ozel = [k.strip() for k in mevcut.split(",") if k.strip()]
        return ozel

    # ==========================
    # TEKRARLAYAN İŞLEMLER
    # ==========================

    def tekrarlayan_ekle(
        self, tur: str, kategori: str, aciklama: str, tutar: float, gun: int
    ) -> None:
        self.cursor.execute(
            "INSERT INTO tekrarlayan (tur, kategori, aciklama, tutar, gun) "
            "VALUES (?,?,?,?,?)",
            (tur, kategori, aciklama, tutar, gun),
        )
        self.conn.commit()

    def tekrarlayan_listele(self) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, tur, kategori, aciklama, tutar, gun, aktif "
            "FROM tekrarlayan ORDER BY tur, kategori"
        )
        return [
            {
                "id": r[0], "tur": r[1], "kategori": r[2],
                "aciklama": r[3], "tutar": r[4], "gun": r[5], "aktif": r[6],
            }
            for r in self.cursor.fetchall()
        ]

    def tekrarlayan_sil(self, id: int) -> None:
        self.cursor.execute("DELETE FROM tekrarlayan WHERE id=?", (id,))
        self.conn.commit()

    def tekrarlayan_toggle(self, id: int) -> None:
        self.cursor.execute(
            "UPDATE tekrarlayan SET aktif = CASE WHEN aktif=1 THEN 0 ELSE 1 END WHERE id=?",
            (id,),
        )
        self.conn.commit()

    def tekrarlayan_bugun_kontrol(self) -> List[Dict[str, Any]]:
        """Bugünün gününde aktif tekrarlayan işlemleri getir."""
        from datetime import datetime
        bugun_gun = datetime.now().day
        self.cursor.execute(
            "SELECT * FROM tekrarlayan WHERE aktif=1 AND gun=?",
            (bugun_gun,),
        )
        return [
            {
                "id": r[0], "tur": r[1], "kategori": r[2],
                "aciklama": r[3], "tutar": r[4], "gun": r[5],
            }
            for r in self.cursor.fetchall()
        ]

    # ==========================
    # TASARRUF HEDEFLERİ
    # ==========================

    def tasarruf_hedefi_ekle(self, ad: str, hedef_tutar: float, hedef_tarih: str = "") -> int:
        hedef_tarih_iso = normalize_date(hedef_tarih) if hedef_tarih else None
        self.cursor.execute(
            "INSERT INTO tasarruf_hedefleri (ad, hedef_tutar, biriken_tutar, hedef_tarih) "
            "VALUES (?, ?, 0, ?)",
            (ad, para_yuvarla(hedef_tutar), hedef_tarih_iso),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def tasarruf_hedefleri_listele(self) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, ad, hedef_tutar, biriken_tutar, hedef_tarih "
            "FROM tasarruf_hedefleri ORDER BY id DESC"
        )
        return [
            {
                "id": r[0], "ad": r[1], "hedef_tutar": float(r[2]),
                "biriken_tutar": float(r[3]), "hedef_tarih": r[4],
            }
            for r in self.cursor.fetchall()
        ]

    def tasarruf_katki_ekle(
        self, id: int, tutar: float, islem_olustur: bool = True,
        tarih: Optional[str] = None,
    ) -> None:
        """Hedefe katkı ekler (negatif tutar geri çekme).

        Önceden katkı yalnızca biriken_tutar'ı güncelliyor, ana işlem
        listesine hiç yansımıyordu: kullanıcı aynı parayı hem 'birikmiş'
        hem 'harcanabilir' görüyordu. Artık katkı 'Tasarruf' kategorisinde
        bir Gider (geri çekme Gelir) işlemi de oluşturur; böylece bakiye
        birikimle tutarlı kalır. Geri çekmede fiilen düşen tutar biriken
        bakiyeyle sınırlanır (MAX(0,...) ile para izi kaybını önler).
        """
        from datetime import date
        katki = para_yuvarla(tutar)
        tarih_iso = normalize_date(tarih) if tarih else date.today().strftime(
            "%Y-%m-%d"
        )
        try:
            self.cursor.execute("BEGIN")
            self.cursor.execute(
                "SELECT ad, biriken_tutar FROM tasarruf_hedefleri WHERE id=?",
                (id,),
            )
            row = self.cursor.fetchone()
            if row is None:
                raise ValueError("Tasarruf hedefi bulunamadı")
            ad, biriken = row[0], float(row[1])
            yeni_biriken = para_yuvarla(max(0.0, biriken + katki))
            fiili_delta = para_yuvarla(yeni_biriken - biriken)

            if islem_olustur and fiili_delta != 0:
                # Birikime giden para Gider, geri çekilen para Gelir
                islem_tur = "Gider" if fiili_delta > 0 else "Gelir"
                self.cursor.execute(
                    "INSERT INTO islemler (tarih, tur, kategori, aciklama, "
                    "tutar, etiketler) VALUES (?,?,?,?,?,?)",
                    (tarih_iso, islem_tur, "Tasarruf",
                     f"Tasarruf: {ad}", abs(fiili_delta), "tasarruf"),
                )
            self.cursor.execute(
                "UPDATE tasarruf_hedefleri SET biriken_tutar=? WHERE id=?",
                (yeni_biriken, id),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def tasarruf_hedefi_sil(self, id: int) -> None:
        self.cursor.execute("DELETE FROM tasarruf_hedefleri WHERE id=?", (id,))
        self.conn.commit()

    # ==========================
    # AYLIK KARŞILAŞTIRMA
    # ==========================

    def aylik_karsilastirma(self) -> Dict[str, Any]:
        """Bu ay ve geçen ayın gelir/gider karşılaştırması."""
        from datetime import datetime
        simdi = datetime.now()
        bu_ay = simdi.month
        bu_yil = simdi.year
        gecen_ay = 12 if bu_ay == 1 else bu_ay - 1
        gecen_yil = bu_yil - 1 if bu_ay == 1 else bu_yil

        def _ay_toplam(ay, yil, tur):
            self.cursor.execute(
                "SELECT COALESCE(SUM(tutar),0) FROM islemler "
                "WHERE tur=? AND CAST(strftime('%m', tarih) AS INTEGER)=? "
                "AND CAST(strftime('%Y', tarih) AS INTEGER)=?",
                (tur, ay, yil),
            )
            row = self.cursor.fetchone()
            return float(row[0]) if row else 0.0

        return {
            "bu_ay": {"ay": bu_ay, "yil": bu_yil,
                      "gelir": _ay_toplam(bu_ay, bu_yil, "Gelir"),
                      "gider": _ay_toplam(bu_ay, bu_yil, "Gider")},
            "gecen_ay": {"ay": gecen_ay, "yil": gecen_yil,
                         "gelir": _ay_toplam(gecen_ay, gecen_yil, "Gelir"),
                         "gider": _ay_toplam(gecen_ay, gecen_yil, "Gider")},
        }

    def yillik_karsilastirma(self) -> List[Tuple[str, float, float]]:
        """(yil, gelir_toplam, gider_toplam) listesi döner — tüm yıllar, eskiden yeniye."""
        self.cursor.execute("""
        SELECT
            strftime('%Y', tarih) AS yil,
            COALESCE(SUM(CASE WHEN tur='Gelir' THEN tutar ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN tur='Gider' THEN tutar ELSE 0 END), 0)
        FROM islemler
        GROUP BY yil
        ORDER BY yil ASC
        """)
        return [(r[0], float(r[1]), float(r[2])) for r in self.cursor.fetchall()]

    # ==========================
    # GÜNLÜK / HAFTALIK FİLTRE
    # ==========================

    def gunluk_islemler(self) -> List[Tuple[Any, ...]]:
        from datetime import date
        bugun = date.today().strftime("%Y-%m-%d")
        self.cursor.execute(
            "SELECT * FROM islemler WHERE tarih=? ORDER BY id DESC", (bugun,)
        )
        return self.cursor.fetchall()

    def haftalik_islemler(self) -> List[Tuple[Any, ...]]:
        from datetime import date, timedelta
        bugun = date.today()
        hafta_basi = (bugun - timedelta(days=bugun.weekday())).strftime("%Y-%m-%d")
        bugun_str = bugun.strftime("%Y-%m-%d")
        self.cursor.execute(
            "SELECT * FROM islemler WHERE tarih BETWEEN ? AND ? ORDER BY id DESC",
            (hafta_basi, bugun_str),
        )
        return self.cursor.fetchall()

    # ==========================
    # KAPAT
    # ==========================

    def close(self) -> None:
        self.conn.close()
