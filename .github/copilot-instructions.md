# Finans Defterim Pro - Copilot Instructions

Bu proje bir Python + CustomTkinter tabanlı gelir/gider kontrol uygulamasıdır.

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

## Testler
- Değişikliklerden sonra şu komutla doğrulama yapın:
  - `python -m unittest discover -s tests -v`
