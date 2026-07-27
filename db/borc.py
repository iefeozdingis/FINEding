"""Borç / alacak işlemleri.

database.py God-object'inden ayrılmıştır; Database sınıfına mixin
olarak eklenir (self üzerinden ortak bağlantı/yardımcıları paylaşır)."""
from datetime import datetime
from typing import Any, Dict, List

from database import normalize_date, para_kurus, para_lira

from db._temel import VeritabaniKarma


class BorcMixin(VeritabaniKarma):
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
            "kalan_tutar, baslangic_tarih, vade_tarih, durum, kullanici_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'Aktif', ?)",
            (tur, aciklama, kisi, para_kurus(toplam), para_kurus(kalan),
             bas_iso, vade_iso, self.aktif_kullanici_id),
        )
        self.conn.commit()
        assert self.cursor.lastrowid is not None
        return self.cursor.lastrowid

    def borc_guncelle(self, id: int, kalan: float, durum: str) -> None:
        self.cursor.execute(
            "UPDATE borclar SET kalan_tutar=?, durum=? WHERE id=? AND kullanici_id=?",
            (para_kurus(kalan), durum, id, self.aktif_kullanici_id),
        )
        self.conn.commit()

    def borc_odeme_yap(
        self, borc_id: int, odeme_tutar: float, tarih: str,
        islem_olustur: bool = False,
    ) -> None:
        """Borç/alacağa ödeme işler: kalanı düşürür, ödeme geçmişine yazar.

        MUHASEBE MODELİ (B): Borç/alacak bir bilanço kalemidir, gelir/gider
        DEĞİL. Bu yüzden ödeme VARSAYILAN OLARAK ana bakiyeye/gelir-gidere
        dokunmaz; borç/alacak durumu ayrı bir "net pozisyon" olarak izlenir
        (bkz. borc_net_pozisyon). Önceki model ödemeyi Gelir/Gider yazıyordu:
        bir alacağı verip tahsil edince bakiye anapara kadar şişiyor, kredili
        alışverişte çift gider sayılıyordu.

        islem_olustur=True verilirse (kullanıcının bilinçli tercihi) ödeme
        ayrıca bir gelir/gider işlemi olarak da kaydedilir — ör. "borcu maaşımdan
        ödedim, bunu harcama defterime de işle" senaryosu.
        """
        # Dış girdi (lira) → kuruş; kalan da kuruş okunur, tüm aritmetik tam
        # sayı kuruşta yürür (float artığı olmadan tam karşılaştırma).
        odeme = para_kurus(odeme_tutar)
        tarih_iso = normalize_date(tarih)
        uid = self.aktif_kullanici_id
        try:
            self.cursor.execute("BEGIN")
            self.cursor.execute(
                "SELECT tur, aciklama, kalan_tutar FROM borclar "
                "WHERE id=? AND kullanici_id=?",
                (borc_id, uid),
            )
            row = self.cursor.fetchone()
            if row is None:
                raise ValueError("Borç kaydı bulunamadı")
            tur, aciklama, kalan = row[0], row[1], int(row[2])
            # Kalanı aşan ödeme kırpılır. Önceden yalnızca yeni_kalan
            # max(0,...) ile kırpılıyor, ödemenin kendisi tam haliyle hem
            # islemler'e hem geçmişe yazılıyordu: kalan 100 TL iken 5000
            # girilince bakiye 4900 TL fazla düşüyordu.
            fiili_odeme = min(odeme, kalan) if odeme > 0 else odeme
            yeni_kalan = max(0, kalan - fiili_odeme)
            yeni_durum = "Ödendi" if yeni_kalan <= 0 else "Aktif"

            if islem_olustur and fiili_odeme != 0:
                islem_tur = "Gider" if tur == "Borç" else "Gelir"
                self.cursor.execute(
                    "INSERT INTO islemler (tarih, tur, kategori, aciklama, "
                    "tutar, etiketler, kullanici_id) VALUES (?,?,?,?,?,?,?)",
                    (tarih_iso, islem_tur, "Borç/Alacak",
                     f"{tur} ödemesi: {aciklama}", fiili_odeme, "borc-odeme", uid),
                )
            self.cursor.execute(
                "INSERT INTO borc_odemeler (borc_id, tarih, tutar) "
                "VALUES (?,?,?)",
                (borc_id, tarih_iso, fiili_odeme),
            )
            self.cursor.execute(
                "UPDATE borclar SET kalan_tutar=?, durum=? WHERE id=? AND kullanici_id=?",
                (yeni_kalan, yeni_durum, borc_id, uid),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def borc_odemeleri(self, borc_id: int) -> List[Dict[str, Any]]:
        """Bir borç/alacağın ödeme geçmişini döner.

        borc_odemeler tablosunda kullanici_id yok; sahiplik borclar tablosuna
        JOIN ile doğrulanır. Filtresiz hali başka kullanıcının ödeme tutar ve
        tarihlerini id denemesiyle okunabilir kılıyordu.
        """
        self.cursor.execute(
            "SELECT o.id, o.tarih, o.tutar FROM borc_odemeler o "
            "JOIN borclar b ON b.id = o.borc_id "
            "WHERE o.borc_id=? AND b.kullanici_id=? "
            "ORDER BY o.tarih",
            (borc_id, self.aktif_kullanici_id),
        )
        return [
            {"id": r[0], "tarih": r[1], "tutar": para_lira(r[2])}
            for r in self.cursor.fetchall()
        ]

    def borc_sil(self, id: int) -> None:
        # Ödeme geçmişi de silinir: yalnızca borclar satırı silindiğinde
        # borc_odemeler'de yetim kayıtlar kalıyor, yeniden kullanılan bir id
        # bu satırları yanlış borca eşleyebiliyordu.
        with self._transaction():
            self.cursor.execute(
                "DELETE FROM borc_odemeler WHERE borc_id IN "
                "(SELECT id FROM borclar WHERE id=? AND kullanici_id=?)",
                (id, self.aktif_kullanici_id),
            )
            self.cursor.execute(
                "DELETE FROM borclar WHERE id=? AND kullanici_id=?",
                (id, self.aktif_kullanici_id),
            )

    def borclari_listele(self, durum: str = "Aktif") -> List[Dict[str, Any]]:
        uid = self.aktif_kullanici_id
        # toplam/kalan KURUŞ saklanır → okuma sınırında lira'ya (÷100.0)
        # çevrilir. Açık kolon listesi kullanici_id'yi zaten dışarıda bırakır.
        secim = (
            "SELECT id, tur, aciklama, kisi, toplam_tutar/100.0, "
            "kalan_tutar/100.0, baslangic_tarih, vade_tarih, durum FROM borclar"
        )
        if durum == "Tümü":
            self.cursor.execute(
                f"{secim} WHERE kullanici_id=? ORDER BY vade_tarih",
                (uid,),
            )
        else:
            self.cursor.execute(
                f"{secim} WHERE durum=? AND kullanici_id=? ORDER BY vade_tarih",
                (durum, uid),
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

    def borc_net_pozisyon(self) -> Dict[str, float]:
        """Aktif kullanıcının borç/alacak net pozisyonunu döner.

        Borç/alacak ana bakiyeye karışmaz (bilanço kalemi); bu metot ayrı
        bir özet sağlar:
          - alacak: başkalarının sana borçlu olduğu kalan toplam
          - borc:   senin başkalarına borçlu olduğun kalan toplam
          - net:    alacak - borc (pozitif = net alacaklısın)
        Kapanmış (kalan=0) kayıtlar toplama katkı vermez.
        """
        self.cursor.execute(
            "SELECT tur, IFNULL(SUM(kalan_tutar), 0) FROM borclar "
            "WHERE kullanici_id=? GROUP BY tur",
            (self.aktif_kullanici_id,),
        )
        alacak = 0  # kuruş
        borc = 0  # kuruş
        for tur, toplam in self.cursor.fetchall():
            if tur == "Alacak":
                alacak = int(toplam)
            elif tur == "Borç":
                borc = int(toplam)
        return {
            "alacak": para_lira(alacak),
            "borc": para_lira(borc),
            "net": para_lira(alacak - borc),
        }

    def yaklasan_borclar(self, gun_esigi: int = 3) -> List[Dict[str, Any]]:
        """Vadesi gun_esigi gün içinde olan veya geçmiş aktif borçları döner
        (aktif kullanıcı için). Bildirim thread'inin iki farklı tarih formatı
        denemesine gerek kalmadı — tarihler artık ISO."""
        from datetime import date as _date
        bugun = _date.today()
        sonuc = []
        for b in self.borclari_listele("Aktif"):
            vade_str = b.get("vade_tarih")
            if not vade_str:
                continue
            try:
                vade = datetime.strptime(vade_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            kalan_gun = (vade - bugun).days
            if kalan_gun <= gun_esigi:
                sonuc.append({**b, "kalan_gun": kalan_gun})
        return sonuc

    def borc_toplam(self, durum: str = "Aktif") -> float:
        self.cursor.execute(
            "SELECT IFNULL(SUM(kalan_tutar), 0) FROM borclar "
            "WHERE durum=? AND kullanici_id=?",
            (durum, self.aktif_kullanici_id),
        )
        row = self.cursor.fetchone()
        return para_lira(row[0]) if row else 0.0
