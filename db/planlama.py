"""Planlama (planlanan gelir/gider) işlemleri.

database.py God-object'inden ayrılmıştır; Database sınıfına mixin
olarak eklenir (self üzerinden ortak bağlantı/yardımcıları paylaşır)."""
from datetime import datetime
from typing import Any, Dict, List, Tuple

from database import normalize_date, para_kurus, para_lira

from db._temel import VeritabaniKarma


class PlanlamaMixin(VeritabaniKarma):
    # ==========================
    # PLANLAMA İŞLEMLERİ
    # ==========================

    def planlanan_ekle(
        self, ay: int, yil: int, kategori: str, tur: str, aciklama: str, tutar: float
    ) -> int:
        self.cursor.execute(
            "INSERT INTO planlanan (ay, yil, kategori, tur, aciklama, tutar, "
            "kullanici_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ay, yil, kategori, tur, aciklama, para_kurus(tutar),
             self.aktif_kullanici_id),
        )
        self.conn.commit()
        assert self.cursor.lastrowid is not None
        return self.cursor.lastrowid

    def planlanan_guncelle(
        self, id: int, kategori: str, tur: str, aciklama: str, tutar: float
    ) -> None:
        self.cursor.execute(
            "UPDATE planlanan SET kategori=?, tur=?, aciklama=?, tutar=? "
            "WHERE id=? AND kullanici_id=?",
            (kategori, tur, aciklama, para_kurus(tutar), id,
             self.aktif_kullanici_id),
        )
        self.conn.commit()

    def planlanan_sil(self, id: int) -> None:
        self.cursor.execute(
            "DELETE FROM planlanan WHERE id=? AND kullanici_id=?",
            (id, self.aktif_kullanici_id),
        )
        self.conn.commit()

    def planlanan_listele(self, ay: int, yil: int) -> List[Tuple[Any, ...]]:
        # tutar KURUŞ saklanır → okuma sınırında lira'ya çevrilir. Kolon
        # SIRASI korunur (UI satir[6]=tutar'a dayanır).
        self.cursor.execute(
            "SELECT id, ay, yil, kategori, tur, aciklama, tutar/100.0, "
            "aktarim_tarihi, kullanici_id FROM planlanan "
            "WHERE ay=? AND yil=? AND kullanici_id=? ORDER BY tur, kategori",
            (ay, yil, self.aktif_kullanici_id),
        )
        return self.cursor.fetchall()

    def planlanan_kopyala(
        self, kaynak_ay: int, kaynak_yil: int, hedef_ay: int, hedef_yil: int,
        uzerine_yaz: bool = False,
    ) -> Dict[str, int]:
        """Bir ayın plan kalemlerini başka aya ATOMİK kopyalar.

        Önceden bu mantık UI'daydı: mevcut kalemleri tek tek silip (ayrı
        commit'ler) sonra yeniden ekliyordu. "Üzerine yaz" sırasında çökme
        olursa hedef ay silinmiş ama kopya yarım kalmış olabiliyordu — hem
        eski hem yeni plan kaybı. Artık tek transaction: ya hepsi ya hiçbiri.

        Dönüş: {"kopyalanan": N, "silinen": M}. uzerine_yaz False iken hedef
        ayda kalem varsa hiçbir şey yapmaz (kopyalanan=-1 ile işaretlenir).
        """
        uid = self.aktif_kullanici_id
        # SELECT * → (id, ay, yil, kategori, tur, aciklama, tutar, ...)
        self.cursor.execute(
            "SELECT kategori, tur, aciklama, tutar FROM planlanan "
            "WHERE ay=? AND yil=? AND kullanici_id=?",
            (kaynak_ay, kaynak_yil, uid),
        )
        kaynak = self.cursor.fetchall()
        if not kaynak:
            return {"kopyalanan": 0, "silinen": 0}

        self.cursor.execute(
            "SELECT COUNT(*) FROM planlanan WHERE ay=? AND yil=? AND kullanici_id=?",
            (hedef_ay, hedef_yil, uid),
        )
        hedef_dolu = self.cursor.fetchone()[0]
        if hedef_dolu and not uzerine_yaz:
            return {"kopyalanan": -1, "silinen": 0}  # çağıran onay istemeli

        with self._transaction():
            silinen = 0
            if hedef_dolu:
                self.cursor.execute(
                    "DELETE FROM planlanan WHERE ay=? AND yil=? AND kullanici_id=?",
                    (hedef_ay, hedef_yil, uid),
                )
                silinen = hedef_dolu
            for kategori, tur, aciklama, tutar in kaynak:
                # tutar DB'den (kuruş) okundu → aynen taşınır; para_kurus ile
                # yeniden çevirmek 100 kat şişirir (iç kopya, dönüşümsüz).
                self.cursor.execute(
                    "INSERT INTO planlanan (ay, yil, kategori, tur, aciklama, "
                    "tutar, kullanici_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (hedef_ay, hedef_yil, kategori, tur, aciklama or "",
                     tutar, uid),
                )
        return {"kopyalanan": len(kaynak), "silinen": silinen}

    def plani_aktar(self, ay: int, yil: int, tarih: str) -> Dict[str, int]:
        """Aktarılmamış plan kalemlerini gerçek işlemlere çevirir.

        Mükerrer aktarım koruması: aktarim_tarihi dolu kalemler atlanır,
        böylece butona ikinci kez basmak gelir/gideri ikiye katlamaz.
        {'aktarilan': N, 'atlanan': M} döner.
        """
        tarih_iso = normalize_date(tarih)
        uid = self.aktif_kullanici_id
        self.cursor.execute(
            "SELECT id, kategori, tur, aciklama, tutar, "
            "COALESCE(aktarim_tarihi,'') FROM planlanan "
            "WHERE ay=? AND yil=? AND kullanici_id=?",
            (ay, yil, uid),
        )
        satirlar = self.cursor.fetchall()
        aktarilan = 0
        atlanan = 0
        bugun = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self._transaction():
            for pid, kategori, tur, aciklama, tutar, aktarim in satirlar:
                if aktarim:
                    atlanan += 1
                    continue
                islem_tur = "Gelir" if tur == "Gelir" else "Gider"
                # planlanan.tutar zaten kuruş; islemler'e dönüşümsüz aktarılır.
                self.cursor.execute(
                    "INSERT INTO islemler (tarih, tur, kategori, aciklama, tutar, "
                    "etiketler, kullanici_id) VALUES (?,?,?,?,?,?,?)",
                    (tarih_iso, islem_tur, kategori, aciklama or "",
                     tutar, "plan", uid),
                )
                self.cursor.execute(
                    "UPDATE planlanan SET aktarim_tarihi=? "
                    "WHERE id=? AND kullanici_id=?",
                    (bugun, pid, uid),
                )
                aktarilan += 1
        return {"aktarilan": aktarilan, "atlanan": atlanan}

    def planlanan_ozet(self, ay: int, yil: int) -> Dict[str, float]:
        self.cursor.execute(
            "SELECT tur, SUM(tutar) FROM planlanan "
            "WHERE ay=? AND yil=? AND kullanici_id=? GROUP BY tur",
            (ay, yil, self.aktif_kullanici_id),
        )
        sonuc = {"Gelir": 0.0, "Gider": 0.0}
        for tur, toplam in self.cursor.fetchall():
            sonuc[tur] = para_lira(toplam)
        return sonuc
