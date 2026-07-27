"""Tasarruf hedefleri.

database.py God-object'inden ayrılmıştır; Database sınıfına mixin
olarak eklenir (self üzerinden ortak bağlantı/yardımcıları paylaşır)."""
from typing import Any, Dict, List, Optional

from database import normalize_date, para_kurus, para_lira

from db._temel import VeritabaniKarma


class TasarrufMixin(VeritabaniKarma):
    # ==========================
    # TASARRUF HEDEFLERİ
    # ==========================

    def tasarruf_hedefi_ekle(self, ad: str, hedef_tutar: float, hedef_tarih: str = "") -> int:
        hedef_tarih_iso = normalize_date(hedef_tarih) if hedef_tarih else None
        self.cursor.execute(
            "INSERT INTO tasarruf_hedefleri (ad, hedef_tutar, biriken_tutar, "
            "hedef_tarih, kullanici_id) VALUES (?, ?, 0, ?, ?)",
            (ad, para_kurus(hedef_tutar), hedef_tarih_iso,
             self.aktif_kullanici_id),
        )
        self.conn.commit()
        assert self.cursor.lastrowid is not None
        return self.cursor.lastrowid

    def tasarruf_hedefleri_listele(self) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, ad, hedef_tutar, biriken_tutar, hedef_tarih "
            "FROM tasarruf_hedefleri WHERE kullanici_id=? ORDER BY id DESC",
            (self.aktif_kullanici_id,),
        )
        return [
            {
                "id": r[0], "ad": r[1], "hedef_tutar": para_lira(r[2]),
                "biriken_tutar": para_lira(r[3]), "hedef_tarih": r[4],
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
        # Dış girdi (lira) → kuruş; biriken de kuruş; aritmetik tam sayıda.
        katki = para_kurus(tutar)
        tarih_iso = normalize_date(tarih) if tarih else date.today().strftime(
            "%Y-%m-%d"
        )
        try:
            self.cursor.execute("BEGIN")
            # kullanici_id filtresi zorunlu: filtresiz SELECT/UPDATE, başka
            # bir kullanıcının hedefinin birikimini değiştirip karşı işlemi
            # çağıranın hesabına yazıyordu (çapraz veri bozulması).
            self.cursor.execute(
                "SELECT ad, biriken_tutar FROM tasarruf_hedefleri "
                "WHERE id=? AND kullanici_id=?",
                (id, self.aktif_kullanici_id),
            )
            row = self.cursor.fetchone()
            if row is None:
                raise ValueError("Tasarruf hedefi bulunamadı")
            ad, biriken = row[0], int(row[1])
            yeni_biriken = max(0, biriken + katki)
            fiili_delta = yeni_biriken - biriken

            if islem_olustur and fiili_delta != 0:
                # Birikime giden para Gider, geri çekilen para Gelir
                islem_tur = "Gider" if fiili_delta > 0 else "Gelir"
                self.cursor.execute(
                    "INSERT INTO islemler (tarih, tur, kategori, aciklama, "
                    "tutar, etiketler, kullanici_id) VALUES (?,?,?,?,?,?,?)",
                    (tarih_iso, islem_tur, "Tasarruf",
                     f"Tasarruf: {ad}", abs(fiili_delta), "tasarruf",
                     self.aktif_kullanici_id),
                )
            self.cursor.execute(
                "UPDATE tasarruf_hedefleri SET biriken_tutar=? "
                "WHERE id=? AND kullanici_id=?",
                (yeni_biriken, id, self.aktif_kullanici_id),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def tasarruf_hedefi_sil(self, id: int) -> None:
        self.cursor.execute(
            "DELETE FROM tasarruf_hedefleri WHERE id=? AND kullanici_id=?",
            (id, self.aktif_kullanici_id),
        )
        self.conn.commit()
