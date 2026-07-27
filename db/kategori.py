"""Özel kategori yönetimi ve öneri.

database.py God-object'inden ayrılmıştır; Database sınıfına mixin
olarak eklenir (self üzerinden ortak bağlantı/yardımcıları paylaşır)."""
from typing import Any, List, Optional

from db._temel import VeritabaniKarma


class KategoriMixin(VeritabaniKarma):
    # ==========================
    # ÖZEL KATEGORİ YÖNETİMİ
    # ==========================

    def _kategori_anahtari(self, tur: str) -> str:
        """Özel kategori ayar anahtarı — KULLANICIYA ÖZEL.

        Önceden anahtar global ("kategoriler_gider") idi; A kullanıcısının
        eklediği özel kategori B kullanıcısının formlarında da görünüyordu.
        Anahtara aktif kullanıcı kimliği eklenerek izolasyon sağlanır.
        """
        return f"kategoriler_{tur.lower()}_{self.aktif_kullanici_id}"

    def kategori_ekle(self, tur: str, kategori: str) -> None:
        """Belirtilen tür (Gelir/Gider) için aktif kullanıcıya özel kategori ekler."""
        anahtar = self._kategori_anahtari(tur)
        mevcut = self.ayar_oku(anahtar, "") or ""
        kategoriler = [k.strip() for k in mevcut.split(",") if k.strip()]
        if kategori not in kategoriler:
            kategoriler.append(kategori)
            self.ayar_kaydet(anahtar, ",".join(kategoriler))

    def kategorileri_getir(self, tur: str) -> List[str]:
        """Aktif kullanıcının özel kategorilerini döner."""
        anahtar = self._kategori_anahtari(tur)
        mevcut = self.ayar_oku(anahtar, "") or ""
        return [k.strip() for k in mevcut.split(",") if k.strip()]

    def kategori_oner(
        self, aciklama: str, tur: Optional[str] = None
    ) -> Optional[str]:
        """Açıklamaya göre en olası kategoriyi önerir (basit keyword eşleştirme).

        Geçmiş işlemler arasında aciklama'yı İÇEREN (LIKE) kayıtlarda en sık
        kullanılan kategoriyi döner; ML yok, tek sorgu. Beraberlikte en son
        kullanılan (MAX(id)) kazanır — kullanıcının güncel alışkanlığı öne
        çıkar. Eşleşme yoksa veya açıklama çok kısaysa None.

        tur verilirse yalnızca o türdeki (Gelir/Gider) işlemlere bakılır;
        böylece aynı açıklama farklı türlerde farklı kategori önerebilir.
        """
        aciklama = (aciklama or "").strip()
        if len(aciklama) < 2:
            return None
        # Kullanıcının yazdığı % ve _ joker olarak yorumlanmasın
        kacisli = (
            aciklama.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        sorgu = (
            "SELECT kategori FROM islemler "
            "WHERE kullanici_id=? AND aciklama LIKE ? ESCAPE '\\'"
        )
        params: List[Any] = [self.aktif_kullanici_id, f"%{kacisli}%"]
        if tur:
            sorgu += " AND tur=?"
            params.append(tur)
        sorgu += " GROUP BY kategori ORDER BY COUNT(*) DESC, MAX(id) DESC LIMIT 1"
        self.cursor.execute(sorgu, tuple(params))
        row = self.cursor.fetchone()
        return row[0] if row else None
