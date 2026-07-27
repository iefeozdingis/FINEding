"""Kullanıcı / kimlik doğrulama işlemleri.

database.py God-object'inden ayrılmıştır; Database sınıfına mixin
olarak eklenir (self üzerinden ortak bağlantı/yardımcıları paylaşır)."""
import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import (
    MIN_SIFRE_UZUNLUK,
    YetkiHatasi,
    _HAS_BCRYPT,
    _KULLANICI_TABLOLARI,
    _sifre_dogrula,
    _sifre_hashla,
)

from db._temel import VeritabaniKarma


class KullaniciMixin(VeritabaniKarma):
    # ==========================
    # KULLANICI İŞLEMLERİ
    # ==========================

    def sifre_dogru_mu(self, sifre: str, kullanici_id: Optional[int] = None) -> bool:
        """Bir kullanıcının şifresini SAYAÇ ARTIRMADAN doğrular.

        kullanici_dogrula (giriş) başarısızlıkta kalıcı kaba-kuvvet sayacını
        artırır. Şifre DEĞİŞTİRME ekranında mevcut şifreyi doğrulamak için o
        yol kullanılınca, kullanıcı kendi şifresini bilmesine rağmen birkaç
        yanlış denemede giriş kilidine takılıyordu. Bu metot yalnızca doğrular,
        yan etkisi yoktur. kullanici_id verilmezse aktif oturum kullanıcısı.
        """
        uid = self.aktif_kullanici_id if kullanici_id is None else kullanici_id
        self.cursor.execute(
            "SELECT sifre_hash FROM kullanicilar WHERE id=?", (uid,)
        )
        row = self.cursor.fetchone()
        return bool(row) and _sifre_dogrula(sifre, row[0])

    def kullanici_dogrula(
        self, kullanici_adi: str, sifre: str
    ) -> Optional[Dict[str, Any]]:
        """Kullanıcı girişi doğrular, başarılıysa kullanıcı bilgilerini döner.

        Başarısız deneme sayacı veritabanında tutulur; giris_kilit_saniyesi()
        ile birlikte pencere kapatıp açarak sıfırlanamayan bir gecikme sağlar.
        """
        self.cursor.execute(
            "SELECT id, kullanici_adi, ad_soyad, sifre_hash FROM kullanicilar "
            "WHERE kullanici_adi=?",
            (kullanici_adi,),
        )
        row = self.cursor.fetchone()
        if row is not None and not _sifre_dogrula(sifre, row[3]):
            self._basarisiz_deneme_kaydet(row[0])
        if row and _sifre_dogrula(sifre, row[3]):
            self.cursor.execute(
                "UPDATE kullanicilar SET basarisiz_deneme=0, son_basarisiz=NULL "
                "WHERE id=?",
                (row[0],),
            )
            self.conn.commit()
            # Upgrade-on-login: eski (bcrypt öncesi) SHA-256 hash başarıyla
            # doğrulandıysa bcrypt'e yükselt; böylece zayıf hash kalıcı olmaz.
            if _HAS_BCRYPT and not str(row[3]).startswith("$2"):
                try:
                    self.cursor.execute(
                        "UPDATE kullanicilar SET sifre_hash=? WHERE id=?",
                        (_sifre_hashla(sifre), row[0]),
                    )
                    self.conn.commit()
                except Exception:
                    logging.getLogger(__name__).warning(
                        "Şifre hash yükseltme başarısız (kullanıcı %s)", row[0]
                    )
            return {"id": row[0], "kullanici_adi": row[1], "ad_soyad": row[2]}
        return None

    def _basarisiz_deneme_kaydet(self, kullanici_id: int) -> None:
        """Başarısız denemeyi kalıcı olarak sayar ve zaman damgasını yeniler."""
        self.cursor.execute(
            "UPDATE kullanicilar SET basarisiz_deneme=COALESCE(basarisiz_deneme,0)+1, "
            "son_basarisiz=? WHERE id=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), kullanici_id),
        )
        self.conn.commit()

    def giris_kilit_saniyesi(self, kullanici_adi: str) -> int:
        """Bu kullanıcı için kalan kilit süresini saniye olarak döner (0 = serbest).

        5 başarısız denemeden sonra üstel gecikme (2^(n-4), en fazla 30 sn)
        uygulanır. Sayaç DB'de tutulduğu için giriş penceresini kapatıp açmak
        ya da uygulamayı yeniden başlatmak gecikmeyi sıfırlamaz.
        """
        self.cursor.execute(
            "SELECT COALESCE(basarisiz_deneme,0), son_basarisiz FROM kullanicilar "
            "WHERE kullanici_adi=?",
            (kullanici_adi,),
        )
        row = self.cursor.fetchone()
        if not row:
            return 0
        deneme, son = int(row[0]), row[1]
        if deneme < 5 or not son:
            return 0
        try:
            son_dt = datetime.strptime(son, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return 0
        bekleme = min(2 ** (deneme - 4), 30)
        gecen = (datetime.now() - son_dt).total_seconds()
        return max(0, int(bekleme - gecen) + (1 if bekleme > gecen else 0))

    def kullanici_kaydet(self, kullanici_adi: str, sifre: str, ad_soyad: str) -> bool:
        """Yeni kullanıcı kaydeder. Başarılıysa True.

        Şifre politikası (min uzunluk) UI'a değil veri katmanına bağlıdır.
        """
        from datetime import datetime as dt

        if len(sifre) < MIN_SIFRE_UZUNLUK:
            raise ValueError(
                f"Şifre en az {MIN_SIFRE_UZUNLUK} karakter olmalıdır."
            )
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
        """Şifre değiştirir. Yetki: aktif kullanıcı ya kendi şifresini ya da
        admin ise başkasınınkini değiştirebilir (yetki kontrolü UI'da değil
        veri katmanında)."""
        if kullanici_id != self.aktif_kullanici_id and not self.aktif_admin_mi():
            raise YetkiHatasi("Bu işlem için yetkiniz yok.")
        if len(yeni_sifre) < MIN_SIFRE_UZUNLUK:
            raise ValueError(
                f"Şifre en az {MIN_SIFRE_UZUNLUK} karakter olmalıdır."
            )
        sifre_hash = _sifre_hashla(yeni_sifre)
        self.cursor.execute(
            "UPDATE kullanicilar SET sifre_hash=? WHERE id=?",
            (sifre_hash, kullanici_id),
        )
        self.conn.commit()

    def kullanici_profil_guncelle(self, kullanici_id: int, ad_soyad: str) -> None:
        """Profil adını günceller. Yetki: kendi profili ya da admin.

        Kontrol yoktu: herhangi bir kullanıcı, id vererek başkasının ad-soyad
        bilgisini değiştirebiliyordu (kullanici_sifre_degistir ve
        kullanici_sil zaten denetliyordu, bu metot asimetrik kalmıştı).
        """
        if kullanici_id != self.aktif_kullanici_id and not self.aktif_admin_mi():
            raise YetkiHatasi("Bu işlem için yetkiniz yok.")
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

    def aktif_admin_mi(self) -> bool:
        """Aktif oturum kullanıcısı admin mi? Yetki kararları paylaşılan
        ayarlar tablosu yerine bellekteki oturum kimliğinden verilir."""
        return self.kullanici_admin_mi(self.aktif_kullanici_id)

    def kullanici_sil(self, kullanici_id: int) -> bool:
        """Kullanıcıyı sil. Yetki: yalnızca admin; admin (id=1) silinemez.

        Yetki kontrolü artık veri katmanında: önceden yalnızca UI admin
        panelini gizliyordu, DB metodu çağıranı hiç doğrulamıyordu.
        """
        if not self.aktif_admin_mi():
            raise YetkiHatasi("Kullanıcı silmek için admin yetkisi gerekir.")
        if kullanici_id == 1:
            return False
        # Silinen kullanıcının finansal verisini de temizle (yetim veri kalmasın).
        # Çok tablolu silme atomik olmalı: yarıda kesilirse kullanıcı silinmiş
        # ama verisi kalmış (ya da tersi) bir ara duruma düşülüyordu.
        with self._transaction():
            # borc_odemeler'de kullanici_id yok; borclar üzerinden temizlenir.
            # Aksi halde borçlar silinince ödeme satırları yetim kalıyordu.
            self.cursor.execute(
                "DELETE FROM borc_odemeler WHERE borc_id IN "
                "(SELECT id FROM borclar WHERE kullanici_id=?)",
                (kullanici_id,),
            )
            for tablo in _KULLANICI_TABLOLARI:
                self.cursor.execute(
                    f"DELETE FROM {tablo} WHERE kullanici_id=?", (kullanici_id,)
                )
            self.cursor.execute(
                "DELETE FROM kullanicilar WHERE id=?", (kullanici_id,)
            )
        return True
