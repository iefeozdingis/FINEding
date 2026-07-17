"""Para ayrıştırma ve biçimlendirme — GUI bağımsız, saf fonksiyonlar.

Bu modül bilinçli olarak tkinter/customtkinter'a bağımlı değildir; böylece
para mantığı headless ortamda (CI dahil) test edilebilir.
"""


def para_parse(metin: str) -> float:
    """Kullanıcı girdisindeki tutarı güvenle float'a çevirir.

    Noktayı koşulsuz binlik ayraç saymak, "12.5" gibi ondalık-noktalı
    girişleri 125'e, "1500.50"yi 150050'ye çeviriyordu (10x-100x hata).
    Türk (1.234,56), ABD (1,234.56) ve sade (12.5 / 12,5) yazımlarının
    hepsi doğru yorumlanır.
    """
    ham = (metin or "").strip().replace("₺", "").replace(" ", "")
    negatif = ham.startswith("-")
    if negatif:
        ham = ham[1:]
    if not ham or any(c not in "0123456789.," for c in ham):
        raise ValueError(f"Geçersiz tutar: {metin!r}")

    son_nokta = ham.rfind(".")
    son_virgul = ham.rfind(",")
    if son_nokta != -1 and son_virgul != -1:
        # İki ayraç da varsa sonda olan ondalık ayracıdır
        ondalik = "." if son_nokta > son_virgul else ","
    elif son_virgul != -1:
        # Tek virgül + 1-2 hane → ondalık (12,5); aksi halde binlik (1,500)
        ondalik = (
            "," if ham.count(",") == 1 and len(ham) - son_virgul - 1 in (1, 2)
            else None
        )
    elif son_nokta != -1:
        # Tek nokta + 1-2 hane → ondalık (12.5); aksi halde binlik (1.500)
        ondalik = (
            "." if ham.count(".") == 1 and len(ham) - son_nokta - 1 in (1, 2)
            else None
        )
    else:
        ondalik = None

    if ondalik:
        binlik = "," if ondalik == "." else "."
        tam, _, kusur = ham.rpartition(ondalik)
        tam = tam.replace(binlik, "")
        if (tam and not tam.isdigit()) or not kusur.isdigit():
            raise ValueError(f"Geçersiz tutar: {metin!r}")
        deger = float(f"{tam or '0'}.{kusur}")
    else:
        temiz = ham.replace(".", "").replace(",", "")
        if not temiz.isdigit():
            raise ValueError(f"Geçersiz tutar: {metin!r}")
        deger = float(temiz)
    return -deger if negatif else deger


def para_formatla(deger: float, sembol: bool = True, ondalik: int = 2) -> str:
    """Tutarı Türk para formatında döner: 1.234,56 ₺ (negatif: -1.234,56 ₺)."""
    metin = f"{abs(deger):,.{ondalik}f}"
    metin = metin.replace(",", "X").replace(".", ",").replace("X", ".")
    isaret = "-" if deger < 0 else ""
    return f"{isaret}{metin} ₺" if sembol else f"{isaret}{metin}"
