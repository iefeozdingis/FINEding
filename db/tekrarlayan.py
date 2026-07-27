"""Tekrarlayan işlem kuralları.

database.py God-object'inden ayrılmıştır; Database sınıfına mixin
olarak eklenir (self üzerinden ortak bağlantı/yardımcıları paylaşır)."""
from typing import Any, Dict, List, Optional

from database import para_kurus, para_lira

from db._temel import VeritabaniKarma


class TekrarlayanMixin(VeritabaniKarma):
    # ==========================
    # TEKRARLAYAN İŞLEMLER
    # ==========================

    def tekrarlayan_ekle(
        self, tur: str, kategori: str, aciklama: str, tutar: float, gun: int,
        bugun: Optional[Any] = None,
    ) -> None:
        """Yeni tekrarlayan kural ekler.

        Kuralın günü BU AY GEÇTİYSE, içinde bulunulan ayı 'işlenmiş' olarak
        işaretleriz (son_islenen_donem). Aksi halde tekrarlayan_isle, yeni
        kuralı geriye dönük bu-ay için hemen ekliyordu → kullanıcı o ayın
        işlemini zaten elle girmişse çift kayıt oluşuyordu. Gün henüz
        gelmediyse boş bırakılır ki kural bu ay, günü gelince çalışsın.

        bugun: test/simülasyon için oluşturulma tarihi (varsayılan gerçek gün).
        """
        from datetime import date
        if bugun is None:
            bugun = date.today()
        son_donem = ""
        if bugun.day >= min(gun, self._ayin_son_gunu(bugun.year, bugun.month)):
            son_donem = f"{bugun.year:04d}-{bugun.month:02d}"
        self.cursor.execute(
            "INSERT INTO tekrarlayan (tur, kategori, aciklama, tutar, gun, "
            "son_islenen_donem, kullanici_id) VALUES (?,?,?,?,?,?,?)",
            (tur, kategori, aciklama, para_kurus(tutar), gun, son_donem,
             self.aktif_kullanici_id),
        )
        self.conn.commit()

    def tekrarlayan_listele(self) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, tur, kategori, aciklama, tutar, gun, aktif "
            "FROM tekrarlayan WHERE kullanici_id=? ORDER BY tur, kategori",
            (self.aktif_kullanici_id,),
        )
        return [
            {
                "id": r[0], "tur": r[1], "kategori": r[2],
                "aciklama": r[3], "tutar": para_lira(r[4]), "gun": r[5],
                "aktif": r[6],
            }
            for r in self.cursor.fetchall()
        ]

    def tekrarlayan_sil(self, id: int) -> None:
        self.cursor.execute(
            "DELETE FROM tekrarlayan WHERE id=? AND kullanici_id=?",
            (id, self.aktif_kullanici_id),
        )
        self.conn.commit()

    def tekrarlayan_toggle(self, id: int) -> None:
        self.cursor.execute(
            "UPDATE tekrarlayan SET aktif = CASE WHEN aktif=1 THEN 0 ELSE 1 END "
            "WHERE id=? AND kullanici_id=?",
            (id, self.aktif_kullanici_id),
        )
        self.conn.commit()

    def tekrarlayan_isle(self, bugun: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Vadesi gelmiş tekrarlayan işlemleri (aktif kullanıcı için) işler.

        Önceki tasarım yalnızca 'bugünün günü == kural günü' ise ekliyordu:
        uygulama o gün kapalıysa o ay tamamen kaçıyor, ayrıca içerik
        eşleştirmeli mükerrer koruması (aciklama NULL olunca) her saat aynı
        kaydı yeniden ekleyebiliyordu. Artık her kural için son işlenen
        dönemden bugüne kadarki tüm 'geçmiş' dönemler (kuralın günü o ay
        gelmişse) telafi edilir ve son_islenen_donem ile işaretlenir.

        Eklenen işlemlerin listesini (bildirim için) döner.
        """
        from datetime import date as _date
        bugun = bugun or _date.today()
        uid = self.aktif_kullanici_id
        eklenenler: List[Dict[str, Any]] = []
        self.cursor.execute(
            "SELECT id, tur, kategori, aciklama, tutar, gun, "
            "COALESCE(son_islenen_donem,'') FROM tekrarlayan "
            "WHERE aktif=1 AND kullanici_id=?",
            (uid,),
        )
        kurallar = self.cursor.fetchall()
        # INSERT + son_islenen_donem UPDATE çifti atomik olmalı: yarıda
        # kesilirse işlem eklenmiş ama dönem işaretlenmemiş olur ve aynı
        # kayıt bir sonraki çalıştırmada tekrar eklenir (mükerrer para).
        with self._transaction():
            for kid, tur, kategori, aciklama, tutar, gun, son_donem in kurallar:
                # Son dönemden sonrası, günü gelmiş dönemler
                for yil, ay in self._islenecek_donemler(son_donem, bugun, gun):
                    gecerli_gun = min(gun, self._ayin_son_gunu(yil, ay))
                    tarih_iso = f"{yil:04d}-{ay:02d}-{gecerli_gun:02d}"
                    # tekrarlayan.tutar zaten kuruş; dönüşümsüz aktarılır.
                    self.cursor.execute(
                        "INSERT INTO islemler (tarih, tur, kategori, aciklama, "
                        "tutar, etiketler, kullanici_id) VALUES (?,?,?,?,?,?,?)",
                        (tarih_iso, tur, kategori, aciklama or "",
                         tutar, "tekrarlayan", uid),
                    )
                    self.cursor.execute(
                        "UPDATE tekrarlayan SET son_islenen_donem=? "
                        "WHERE id=? AND kullanici_id=?",
                        (f"{yil:04d}-{ay:02d}", kid, uid),
                    )
                    eklenenler.append(
                        {"tur": tur, "kategori": kategori,
                         "tutar": para_lira(tutar)}  # bildirim için lira
                    )
        return eklenenler

    @staticmethod
    def _ayin_son_gunu(yil: int, ay: int) -> int:
        import calendar
        return calendar.monthrange(yil, ay)[1]

    @classmethod
    def _islenecek_donemler(cls, son_donem: str, bugun: Any, gun: int):
        """(yil, ay) çiftlerini üretir: son_donem'den sonraki, kuralın günü
        gelmiş dönemler. son_donem boşsa yalnızca içinde bulunulan ay
        (günü gelmişse) işlenir — geçmişe dönük sınırsız üretim yapılmaz."""
        bu_yil, bu_ay = bugun.year, bugun.month
        if son_donem:
            try:
                y, a = int(son_donem[:4]), int(son_donem[5:7])
            except (ValueError, IndexError):
                y, a = bu_yil, bu_ay
            # son dönemden bir sonraki aydan başla
            a += 1
            if a > 12:
                a = 1
                y += 1
        else:
            # İlk kez: yalnızca içinde bulunulan ayı değerlendir
            y, a = bu_yil, bu_ay
        while (y, a) <= (bu_yil, bu_ay):
            # Bu dönemde kuralın günü geldi mi? (içinde bulunulan ay için
            # bugünün günü >= kural günü olmalı; geçmiş aylar her zaman geçmiş)
            if (y, a) < (bu_yil, bu_ay) or bugun.day >= min(
                gun, cls._ayin_son_gunu(y, a)
            ):
                yield (y, a)
            a += 1
            if a > 12:
                a = 1
                y += 1

    # tekrarlayan_bugun_kontrol kaldırıldı: hiçbir yerden çağrılmıyordu ve
    # kullanici_id filtresi olmadığı için canlandırıldığı anda tüm
    # kullanıcıların tekrarlayan kurallarını sızdıracaktı. Gerçek işleme
    # yolu tekrarlayan_isle() (izolasyonlu) üzerinden yürüyor.
