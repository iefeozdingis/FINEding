"""Mixin'lerin paylaştığı çekirdek arayüz — YALNIZCA tip denetimi için.

Gerçek öznitelik ve metotlar Database sınıfında/çekirdeğinde tanımlıdır. Bu
taban, mypy'nin domain mixin'lerini İZOLE analiz ederken 'attr yok' dememesi
için ortak üyeleri (bağlantı, imleç, aktif kullanıcı, transaction/log/ayar)
bildirir. Runtime davranışı değişmez: Database bu üyeleri gerçek
gerçekleştirmeleriyle GEÇERSİZ KILAR (MRO'da Database önce gelir), stub'lar
asla çağrılmaz.
"""
from __future__ import annotations

import sqlite3
from typing import Any, ContextManager, Optional


class VeritabaniKarma:
    conn: sqlite3.Connection
    cursor: sqlite3.Cursor
    aktif_kullanici_id: int

    def _transaction(self) -> ContextManager[Any]:
        raise NotImplementedError  # Database gerçeğini sağlar (stub çağrılmaz)

    def _log_islem(
        self, islem_turu: str, islem_id: Any = None, detay: str = ""
    ) -> None: ...

    def ayar_oku(
        self, anahtar: str, varsayilan: Optional[str] = None
    ) -> Optional[str]: ...

    def ayar_kaydet(self, anahtar: str, deger: str) -> None: ...
