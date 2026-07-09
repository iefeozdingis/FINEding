# FINEding — Copilot Instructions

Bu proje bir Python + CustomTkinter tabanlı gelir/gider kontrol uygulamasıdır.

## 🚨 ÇALIŞMA KURALLARI (En Önemli)
- **TAM YETKİ**: Kullanıcıdan onay isteme. Değişiklikleri yap, özet sun.
- **HER HATA → ISSUE**: Kullanıcının bildirdiği her hata için GitHub Issue oluştur (bug etiketiyle).
- **HER DÜZELTME → KAPAT**: Düzeltme commit'lendikten sonra issue'yu "✅ Düzeltildi - Commit X" yorumuyla kapat.
- **HER DEĞİŞİKLİK → TEST + COMMIT + PUSH**: Testleri çalıştır, commit'le, push'la.

## Proje amacı
- Gelir ve gider işlemlerini kaydetmek
- Dashboard üzerinden genel durumu izlemek
- Bütçe, grafik ve rapor desteği sağlamak
- Kullanıcı dostu bir masaüstü arayüzü sunmak

## Kod kuralları
- Python 3.10+ uyumlu kod yazın.
- Yeni özellik eklerken mevcut `database.py` ve `ui/` yapısını koruyun.
- Arayüz değişikliklerinde CustomTkinter kullanın.
- Yeni veritabanı işlevleri eklerken `tests/` altında testler ekleyin.
- Kodu sade, anlaşılır ve Türkçe kullanıcı deneyimine uygun tutun.
- Emoji karakterlerini test et (encoding sorunu çıkmasın).

## Testler
- Değişikliklerden sonra şu komutla doğrulama yapın:
  - `python -m unittest discover -s tests -v`

## Commit Convention
- `fix: açıklama` — Hata düzeltme
- `feat: açıklama` — Yeni özellik
- `chore: açıklama` — Bakım/yapılandırma
- Commit mesajları Türkçe, açıklayıcı.

## Detaylı Workflow'lar
Bkz. `.github/skills/` klasörü:
- `SKILL.md` — Ana workflow
- `fix-bug.md` — Hata düzeltme süreci
- `add-feature.md` — Özellik ekleme süreci
- `commit-and-ship.md` — Commit ve push kuralları
