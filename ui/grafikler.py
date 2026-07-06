from datetime import datetime
import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class GrafiklerSayfasi(ctk.CTkFrame):

    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent)
        self.db = db
        self.dashboard_callback = dashboard_callback
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="📊 Grafikler", font=("Segoe UI", 28, "bold")).pack(pady=20)

        fig = Figure(figsize=(8, 6), dpi=100)
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)

        aylik = self._aylik_veri()
        aylar = list(aylik["Gelir"].keys())
        if len(aylar) < 2:
            aylar = [datetime.now().strftime("%Y-%m")]

        gelir_deger = [aylik["Gelir"].get(ay, 0) for ay in aylar]
        gider_deger = [aylik["Gider"].get(ay, 0) for ay in aylar]
        ax1.bar(aylar, gelir_deger, color="#2e8b57", label="Gelir")
        ax1.bar(aylar, [-x for x in gider_deger], color="#c0392b", label="Gider")
        ax1.set_title("Aylık Gelir / Gider")
        ax1.set_ylabel("₺")
        ax1.legend()

        gelirler = self.db.kategori_toplamlari("Gelir")
        if gelirler:
            labels = [item[0] for item in gelirler[:5]]
            values = [item[1] for item in gelirler[:5]]
            ax2.pie(values, labels=labels, autopct="%1.1f%%")
            ax2.set_title("Gelir Kategori Dağılımı")
        else:
            ax2.text(0.5, 0.5, "Henüz gelir verisi yok", ha="center", va="center")
            ax2.set_title("Gelir Kategori Dağılımı")

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)

    def _aylik_veri(self):
        data = {"Gelir": {}, "Gider": {}}
        for _, tarih, tur, _, _, tutar in self.db.tum_islemler():
            try:
                dt = datetime.strptime(tarih, "%d.%m.%Y")
            except ValueError:
                continue
            anahtar = dt.strftime("%Y-%m")
            data[tur][anahtar] = data[tur].get(anahtar, 0) + float(tutar)
        return data
