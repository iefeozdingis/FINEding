---
name: fineding-workflow
description: FINEding projesi için tam geliştirme workflow'u. Hata düzeltme, özellik ekleme, test, commit ve issue yönetimini kapsar.
applyTo: "**/*.py"
---

# FINEding Geliştirme Workflow'u

## Proje Hakkında
Python + CustomTkinter tabanlı gelir/gider kontrol uygulaması.
Kullanıcı: @iefeozdingis — TAM YETKİLİ, onay sorma, direkt yap.

## Çalışma Kuralları
1. **Asla onay sorma.** Değişiklikleri yap, özet sun.
2. **Her hata için GitHub Issue oluştur** (bug etiketiyle).
3. **Düzeltince issue'yu kapat** — "✅ Düzeltildi - Commit X" yorumuyla.
4. **Her değişiklik sonrası test çalıştır:** `python -m unittest discover -s tests -v`
5. **Commit mesajları Türkçe, açıklayıcı ve convention'lı:** `fix:`, `feat:`, `chore:`
6. **Değişiklikleri hemen push'la.**

## Kod Kuralları
- Python 3.10+ uyumlu
- CustomTkinter arayüz için
- `database.py` ve `ui/` yapısını koru
- Türkçe kullanıcı deneyimi
- Emoji karakterleri test et (encoding sorunu olmasın)

## Yasaklı Davranışlar (Anti-Rationalization)
| Bahane | Gerçek |
|--------|--------|
| "Sonra test eklerim" | Şimdi ekle, yoksa hiç eklenmez |
| "Issue'yu sonra açarım" | Unutulur, hemen aç |
| "Kullanıcıya sorayım" | SORMA. TAM YETKİLİSİN. |
| "Browser otomasyonu zor" | Dene, başarısız olursa alternatif bul |
