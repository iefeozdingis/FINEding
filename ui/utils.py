"""Otomatik formatlama yardımcıları — tarih ve para girişi için."""

from tkinter import ttk

import customtkinter as ctk

# Saf para fonksiyonları GUI'siz money modülünde yaşar (test edilebilirlik);
# geriye dönük uyumluluk için buradan yeniden ihraç edilir.
from ui.money import para_formatla, para_parse

__all__ = [
    "para_formatla",
    "para_parse",
    "tema_renkleri",
    "treeview_tema_uygula",
    "tarih_formatla",
    "tutar_formatla",
    "tarih_bind",
    "tutar_bind",
    "tutar_oku",
]


def tema_renkleri():
    """Uygulamanın aydınlık/karanlık moduna göre renk paleti döner."""
    if ctk.get_appearance_mode() == "Dark":
        return {
            "arka_plan": "#2b2b2b",
            "baslik_arka_plan": "#333333",
            "metin": "#DCE4EE",
            "secili": "#0f766e",
            "secili_metin": "#DCE4EE",
            "izgara": "#3f3f3f",
        }
    return {
        "arka_plan": "#dbdbdb",
        "baslik_arka_plan": "#cfcfcf",
        "metin": "#1a1a1a",
        "secili": "#0d9488",
        "secili_metin": "#DCE4EE",
        "izgara": "#b5b5b5",
    }


def treeview_tema_uygula():
    """Treeview tablolarını (Dashboard, Planlama) mevcut temaya göre boyar.

    ttk widget'ları CustomTkinter'ın tema sisteminin dışında kaldığı için
    varsayılan olarak her zaman OS'un açık renk temasıyla çiziliyorlardı.
    """
    renk = tema_renkleri()
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "Treeview",
        background=renk["arka_plan"],
        foreground=renk["metin"],
        fieldbackground=renk["arka_plan"],
        borderwidth=0,
        rowheight=28,
    )
    style.map(
        "Treeview",
        background=[("selected", renk["secili"])],
        foreground=[("selected", renk["secili_metin"])],
    )
    style.configure(
        "Treeview.Heading",
        background=renk["baslik_arka_plan"],
        foreground=renk["metin"],
        borderwidth=0,
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", renk["baslik_arka_plan"])],
    )


def modal_yap(pencere, parent) -> None:
    """Toplevel'i modal hale getirir (arkaya kaçmaz, ana pencere tıklanamaz).

    Bu blok 10 ayrı pencerede birebir kopyalanmıştı; modal davranışındaki
    bir düzeltmenin hepsinde elle tekrarlanması gerekiyordu ve biri
    unutulunca davranış sapıyordu.
    """
    pencere.transient(parent.winfo_toplevel())
    pencere.grab_set()
    pencere.lift()
    pencere.focus_force()
    pencere.protocol("WM_DELETE_WINDOW", pencere.destroy)


def kategori_listesi(db, tur: str) -> list:
    """Varsayılan + kullanıcının özel kategorilerini (tekrarsız) döner.

    Aynı birleştirme mantığı üç ayrı yerde kopyalanmıştı (islem_formu,
    dashboard._kategoriler, dashboard._hizli_islem); kural değişince biri
    unutulursa formlar arası tutarsız kategori listeleri oluşuyordu.
    """
    from ui.gelir import VARSAYILAN_GELIR_KATEGORILER
    from ui.gider import VARSAYILAN_GIDER_KATEGORILER

    varsayilan = (
        VARSAYILAN_GELIR_KATEGORILER if tur == "Gelir"
        else VARSAYILAN_GIDER_KATEGORILER
    )
    ozel = db.kategorileri_getir(tur)
    return list(varsayilan) + [k for k in ozel if k not in varsayilan]


def tarih_bicimle(rakamlar: str) -> str:
    """Yalnızca rakamlardan oluşan metni GG.AA.YYYY biçimine sokar.

    SAF fonksiyon — widget'a bağlı değil, headless test edilebilir. Mantık
    önceden tamamen tarih_formatla(event) içinde, event.widget'a kilitliydi;
    bu yüzden testler gerçek bir tk.Entry kurmak zorundaydı (yavaş, DISPLAY
    bağımlı) ve sınır durumları kapsanmıyordu.

    >>> tarih_bicimle("01")
    '01'
    >>> tarih_bicimle("0107")
    '01.07'
    >>> tarih_bicimle("01072026")
    '01.07.2026'
    """
    rakamlar = "".join(c for c in rakamlar if c.isdigit())
    if len(rakamlar) <= 2:
        return rakamlar
    if len(rakamlar) <= 4:
        return f"{rakamlar[:2]}.{rakamlar[2:]}"
    # 8 haneden fazlası yok sayılır (GGAAYYYY)
    return f"{rakamlar[:2]}.{rakamlar[2:4]}.{rakamlar[4:8]}"


def tarih_formatla(event=None):
    """CTkEntry içinde GG.AA.YYYY formatını otomatik uygular."""
    widget = event.widget

    # Backspace/Delete ise formatlama yapma, kullanıcının silmesine izin ver
    if event and event.keysym in (
        "BackSpace",
        "Delete",
        "Left",
        "Right",
        "Home",
        "End",
        "Tab",
    ):
        return

    eski_metin = widget.get()
    eski_pos = widget.index("insert")

    metin = "".join(c for c in eski_metin if c.isdigit())
    if not metin:
        # Sadece noktalar varsa tamamen temizle
        if eski_metin.replace(".", "").strip() == "":
            widget.delete(0, "end")
        return

    yeni = tarih_bicimle(metin)

    widget.delete(0, "end")
    widget.insert(0, yeni)

    # Cursor'ı mümkün olduğunca eski yerine yakın tut
    dot_sayisi_eski = eski_metin[:eski_pos].count(".")
    yeni_pos = eski_pos
    if dot_sayisi_eski < yeni[:eski_pos].count("."):
        yeni_pos += 1
    widget.icursor(min(yeni_pos, len(yeni)))


def tutar_formatla(event=None):
    """CTkEntry içinde para formatını otomatik uygular (1.500,75 gibi)."""
    widget = event.widget

    # Navigation tuşlarında formatlama yapma
    if event and event.keysym in ("Left", "Right", "Home", "End", "Tab"):
        return

    ham = widget.get().strip()
    if not ham:
        return

    eski_pos = widget.index("insert")

    if "," in ham:
        parts = ham.split(",")
        # Kuruş en fazla 2 hane: 3. hane "10,999" gibi ekranda 11,00
        # görünen ama 10.999 kaydedilen tutarsız değerler üretiyordu
        kurus = "".join(c for c in parts[-1] if c.isdigit())[:2]
        tam_kisim = "".join(c for c in ",".join(parts[:-1]) if c.isdigit())
    else:
        kurus = None
        tam_kisim = "".join(c for c in ham if c.isdigit())

    if not tam_kisim:
        if kurus:
            widget.delete(0, "end")
            widget.insert(0, f"0,{kurus}")
        return

    # Binlik ayraç ekle
    sayi = int(tam_kisim)
    tam_formatli = f"{sayi:,}".replace(",", ".")

    if kurus is not None:
        yeni = f"{tam_formatli},{kurus}"
    else:
        yeni = tam_formatli

    # Cursor pozisyonunu koru: nokta eklendiyse cursor'ı 1 ilerlet
    eski_nokta = widget.get()[:eski_pos].count(".")
    widget.delete(0, "end")
    widget.insert(0, yeni)
    yeni_nokta = yeni[:eski_pos].count(".")
    yeni_pos = eski_pos + (yeni_nokta - eski_nokta)
    widget.icursor(min(yeni_pos, len(yeni)))


def tarih_bind(widget):
    """Widget'a tarih formatlama binding'i ekle."""
    widget.bind("<KeyRelease>", tarih_formatla)


def tutar_bind(widget):
    """Widget'a para formatlama binding'i ekle."""
    widget.bind("<KeyRelease>", tutar_formatla)


def tutar_oku(widget) -> float:
    """Formatlı tutar widget'ından float değer okur."""
    return para_parse(widget.get())
