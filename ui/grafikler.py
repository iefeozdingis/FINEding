from datetime import datetime

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from ui.utils import tema_renkleri


class GrafiklerSayfasi(ctk.CTkFrame):
    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent)
        self.db = db
        self.dashboard_callback = dashboard_callback
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="📊 Grafikler", font=("Segoe UI", 28, "bold")).pack(
            pady=(20, 5)
        )

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))
        ctk.CTkButton(
            btn_frame,
            text="🔄 Grafikleri Yenile",
            width=200,
            fg_color="#0d9488",
            command=self._grafik_ciz,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="📊 Bu Ay vs Geçen Ay",
            width=180,
            fg_color="#6366f1",
            command=self._aylik_karsilastirma_ciz,
        ).pack(side="left", padx=5)

        self._grafik_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._grafik_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self._grafik_ciz()

    def _grafik_stil_uygula(self, fig, *eksenler, pasta_metinler=()):
        """Figure/axes'i mevcut aydınlık/karanlık temaya göre boyar.

        matplotlib varsayılan olarak her zaman beyaz arka plan çizer;
        bu yüzden karanlık modda grafikler tema dışı kalıyordu.
        """
        renk = tema_renkleri()
        fig.patch.set_facecolor(renk["arka_plan"])
        for ax in eksenler:
            ax.set_facecolor(renk["arka_plan"])
            ax.tick_params(colors=renk["metin"])
            ax.xaxis.label.set_color(renk["metin"])
            ax.yaxis.label.set_color(renk["metin"])
            ax.title.set_color(renk["metin"])
            for spine in ax.spines.values():
                spine.set_color(renk["izgara"])
            legend = ax.get_legend()
            if legend:
                legend.get_frame().set_facecolor(renk["arka_plan"])
                legend.get_frame().set_edgecolor(renk["izgara"])
                for text in legend.get_texts():
                    text.set_color(renk["metin"])
        for metin_grubu in pasta_metinler:
            for text in metin_grubu:
                text.set_color(renk["metin"])

    def _grafik_ciz(self):
        for widget in self._grafik_frame.winfo_children():
            widget.destroy()

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

        renk = tema_renkleri()
        pasta_metinler = []

        gelirler = self.db.kategori_toplamlari("Gelir")
        if gelirler:
            labels = [item[0] for item in gelirler[:5]]
            values = [item[1] for item in gelirler[:5]]
            _, metin1, autometin1 = ax2.pie(values, labels=labels, autopct="%1.1f%%")
            pasta_metinler.append(metin1)
            pasta_metinler.append(autometin1)
            ax2.set_title("Gelir Kategori Dağılımı")
        else:
            ax2.text(0.5, 0.5, "Henüz gelir verisi yok", ha="center", va="center", color=renk["metin"])
            ax2.set_title("Gelir Kategori Dağılımı")

        # Gider pasta grafiği (yeni)
        fig2 = Figure(figsize=(4, 3), dpi=100)
        ax3 = fig2.add_subplot(111)
        giderler = self.db.kategori_toplamlari("Gider")
        if giderler:
            labels2 = [item[0] for item in giderler[:5]]
            values2 = [item[1] for item in giderler[:5]]
            _, metin2, autometin2 = ax3.pie(
                values2,
                labels=labels2,
                autopct="%1.1f%%",
                colors=["#c0392b", "#e74c3c", "#e67e22", "#f39c12", "#d35400"],
            )
            pasta_metinler.append(metin2)
            pasta_metinler.append(autometin2)
            ax3.set_title("Gider Kategori Dağılımı")
        else:
            ax3.text(0.5, 0.5, "Henüz gider verisi yok", ha="center", va="center", color=renk["metin"])
            ax3.set_title("Gider Kategori Dağılımı")

        self._grafik_stil_uygula(fig, ax1, ax2, pasta_metinler=pasta_metinler[:2])
        self._grafik_stil_uygula(fig2, ax3, pasta_metinler=pasta_metinler[2:])

        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=self._grafik_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, pady=(10, 0))

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self._grafik_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _aylik_veri(self):
        """SQL tabanlı aylık özet — tüm veriyi RAM'e çekmez."""
        data = {"Gelir": {}, "Gider": {}}
        for ay, gelir, gider in self.db.aylik_ozet():
            data["Gelir"][ay] = gelir
            data["Gider"][ay] = gider
        return data

    def _aylik_karsilastirma_ciz(self):
        """Bu ay vs geçen ay karşılaştırma grafiği."""
        for widget in self._grafik_frame.winfo_children():
            widget.destroy()

        kars = self.db.aylik_karsilastirma()
        bu = kars["bu_ay"]
        gecen = kars["gecen_ay"]

        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)

        kategoriler = ["Gelir", "Gider"]
        bu_deger = [bu["gelir"], bu["gider"]]
        gecen_deger = [gecen["gelir"], gecen["gider"]]

        x = range(len(kategoriler))
        w = 0.35
        ax.bar([i - w / 2 for i in x], bu_deger, w, color="#14b8a6", label=f"Bu Ay ({bu['ay']:02d}/{bu['yil']})")
        ax.bar([i + w / 2 for i in x], gecen_deger, w, color="#475569", label=f"Geçen Ay ({gecen['ay']:02d}/{gecen['yil']})")
        ax.set_xticks(x)
        ax.set_xticklabels(kategoriler)
        ax.set_ylabel("₺")
        ax.set_title("📊 Bu Ay vs Geçen Ay")
        ax.legend()

        renk = tema_renkleri()
        # Değerleri barların üstüne yaz
        for i, v in enumerate(bu_deger):
            ax.text(i - w / 2, v + 50, f"{v:,.0f}", ha="center", fontsize=9, color=renk["metin"])
        for i, v in enumerate(gecen_deger):
            ax.text(i + w / 2, v + 50, f"{v:,.0f}", ha="center", fontsize=9, color=renk["metin"])

        self._grafik_stil_uygula(fig, ax)

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self._grafik_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
