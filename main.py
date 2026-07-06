import customtkinter as ctk

from database import Database
from ui.dashboard import Dashboard
from ui.gelir import GelirSayfasi
from ui.gider import GiderSayfasi
from ui.butce import ButceSayfasi
from ui.raporlar import RaporlarSayfasi
from ui.grafikler import GrafiklerSayfasi
from ui.ayarlar import AyarlarSayfasi


ctk.set_default_color_theme("blue")


class FinansDefterim(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("💰 Finans Defterim Pro")
        self.geometry("1400x800")
        self.minsize(1200,700)

        self.db = Database()
        tema = self.db.ayar_oku("tema", "dark")
        ctk.set_appearance_mode(tema)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.menu = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0
        )

        self.menu.grid(
            row=0,
            column=0,
            sticky="ns"
        )

        self.content = ctk.CTkFrame(
            self,
            corner_radius=0
        )

        self.content.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=10,
            pady=10
        )

        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.menu_olustur()

        self.dashboard_ac()    

    # =====================================
    # SOL MENÜ
    # =====================================

    def menu_olustur(self):

        ctk.CTkLabel(
            self.menu,
            text="💰\nFinans\nDefterim",
            font=("Segoe UI", 28, "bold")
        ).pack(pady=30)

        self.btn_dashboard = ctk.CTkButton(
            self.menu,
            text="🏠 Dashboard",
            height=45,
            command=self.dashboard_ac
        )
        self.btn_dashboard.pack(fill="x", padx=15, pady=6)

        self.btn_gelir = ctk.CTkButton(
            self.menu,
            text="💰 Gelir",
            height=45,
            command=self.gelir_ac
        )
        self.btn_gelir.pack(fill="x", padx=15, pady=6)

        self.btn_gider = ctk.CTkButton(
            self.menu,
            text="💸 Gider",
            height=45,
            command=self.gider_ac
        )
        self.btn_gider.pack(fill="x", padx=15, pady=6)

        self.btn_grafikler = ctk.CTkButton(
            self.menu,
            text="📊 Grafikler",
            height=45,
            command=self.grafikler_ac
        )
        self.btn_grafikler.pack(fill="x", padx=15, pady=6)

        self.btn_raporlar = ctk.CTkButton(
            self.menu,
            text="📄 Raporlar",
            height=45,
            command=self.raporlar_ac
        )
        self.btn_raporlar.pack(fill="x", padx=15, pady=6)

        self.btn_butce = ctk.CTkButton(
            self.menu,
            text="📅 Bütçe",
            height=45,
            command=self.butce_ac
        )
        self.btn_butce.pack(fill="x", padx=15, pady=6)

        self.btn_ayarlar = ctk.CTkButton(
            self.menu,
            text="⚙️ Ayarlar",
            height=45,
            command=self.ayarlar_ac
        )
        self.btn_ayarlar.pack(fill="x", padx=15, pady=6)

    # =====================================
    # SAYFA TEMİZLE
    # =====================================

    def temizle(self):

        for widget in self.content.winfo_children():
            widget.destroy()
    
    # =====================================
    # DASHBOARD
    # =====================================

    def dashboard_ac(self):

        self.temizle()

        self.dashboard = Dashboard(
            self.content,
            self.db
        )

        self.dashboard.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

    # =====================================
    # GELİR SAYFASI
    # =====================================

    def gelir_ac(self):

        self.temizle()

        self.gelir = GelirSayfasi(
            self.content,
            self.db,
            dashboard_callback=self.dashboard_ac
        )

        self.gelir.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

    # =====================================
    # GİDER SAYFASI
    # =====================================

    def gider_ac(self):

        self.temizle()

        self.gider = GiderSayfasi(
            self.content,
            self.db,
            dashboard_callback=self.dashboard_ac
        )

        self.gider.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

    # =====================================
    # RAPORLAR
    # =====================================

    def raporlar_ac(self):

        self.temizle()

        self.raporlar = RaporlarSayfasi(
            self.content,
            self.db,
            dashboard_callback=self.dashboard_ac
        )

        self.raporlar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

    # =====================================
    # BÜTÇE
    # =====================================

    def butce_ac(self):

        self.temizle()

        self.butce = ButceSayfasi(
            self.content,
            self.db,
            dashboard_callback=self.dashboard_ac
        )

        self.butce.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

    # =====================================
    # GRAFİKLER
    # =====================================

    def grafikler_ac(self):

        self.temizle()

        self.grafikler = GrafiklerSayfasi(
            self.content,
            self.db,
            dashboard_callback=self.dashboard_ac
        )

        self.grafikler.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

    # =====================================
    # AYARLAR
    # =====================================

    def ayarlar_ac(self):

        self.temizle()

        self.ayarlar = AyarlarSayfasi(
            self.content,
            self.db,
            dashboard_callback=self.dashboard_ac
        )

        self.ayarlar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

    # =====================================
    # ÇIKIŞ
    # =====================================

    def cikis(self):

        self.db.close()

        self.destroy()


if __name__ == "__main__":

    app = FinansDefterim()

    app.protocol(
        "WM_DELETE_WINDOW",
        app.cikis
    )

    app.mainloop()