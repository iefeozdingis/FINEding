"""Hakkında sayfası."""

import customtkinter as ctk


class HakkindaSayfasi(ctk.CTkFrame):
    def __init__(self, parent, db, dashboard_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Scrollable kart
        kart = ctk.CTkScrollableFrame(
            self,
            corner_radius=20,
            fg_color="#134e4a",
            border_width=1,
            border_color="#14b8a6",
        )
        kart.pack(pady=30, padx=60, fill="both", expand=True)

        # Logo
        ctk.CTkLabel(kart, text="💎", font=("Segoe UI Emoji", 60)).pack(pady=(30, 5))

        ctk.CTkLabel(
            kart, text="Fineding", font=("Segoe UI", 28, "bold"), text_color="#5eead4"
        ).pack()

        ctk.CTkLabel(
            kart, text="v1.0.0", font=("Segoe UI", 13), text_color="#64748b"
        ).pack(pady=(0, 15))

        # Ayraç
        ctk.CTkFrame(kart, height=1, fg_color="#334155").pack(
            fill="x", padx=80, pady=10
        )

        # Açıklama
        ctk.CTkLabel(
            kart,
            text=(
                "Fineding, kişisel finans yönetiminizi\n"
                "kolaylaştırmak için tasarlanmış kapsamlı bir masaüstü uygulamasıdır."
            ),
            font=("Segoe UI", 14),
            text_color="#cbd5e1",
            justify="center",
        ).pack(pady=(10, 5))

        # Özellikler
        ctk.CTkLabel(
            kart,
            text="✨ Özellikler",
            font=("Segoe UI", 17, "bold"),
            text_color="#2dd4bf",
        ).pack(pady=(20, 8))

        ozellikler = [
            "💰 Gelir ve gider takibi",
            "📅 Aylık bütçe yönetimi",
            "💳 Borç ve alacak takibi",
            "📋 Gelecek ay planlaması",
            "📊 Grafiklerle görsel analiz",
            "📄 CSV, Excel ve PDF raporları",
            "🔐 Çok kullanıcılı giriş sistemi",
            "🎨 Karanlık tema desteği",
            "⌨️ Klavye kısayolları",
            "💾 Otomatik yedekleme",
        ]

        for ozellik in ozellikler:
            ctk.CTkLabel(
                kart,
                text=f"  • {ozellik}",
                font=("Segoe UI", 13),
                text_color="#94a3b8",
                anchor="w",
            ).pack(pady=2)

        # Ayraç
        ctk.CTkFrame(kart, height=1, fg_color="#334155").pack(
            fill="x", padx=80, pady=15
        )

        # Teknoloji
        ctk.CTkLabel(
            kart,
            text="🛠️ Teknolojiler",
            font=("Segoe UI", 15, "bold"),
            text_color="#a78bfa",
        ).pack(pady=(5, 5))

        ctk.CTkLabel(
            kart,
            text="Python • CustomTkinter • SQLite • Matplotlib • ReportLab • OpenPyXL • Pillow",
            font=("Segoe UI", 12),
            text_color="#64748b",
        ).pack(pady=(0, 5))

        # Telif
        ctk.CTkLabel(
            kart,
            text="© 2026 Fineding — Tüm hakları saklıdır.",
            font=("Segoe UI", 11),
            text_color="#475569",
        ).pack(pady=(15, 25))
