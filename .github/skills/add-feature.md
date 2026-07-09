---
name: add-feature
description: Yeni özellik eklerken uygulanacak workflow.
---

# ✨ Özellik Ekleme Workflow'u

## Süreç

### 1. PLANLA
- Özelliği anla, kapsamı belirle
- Hangi dosyalar etkilenecek?
- Veritabanı değişikliği var mı?
- UI değişikliği var mı?

### 2. ISSUE OLUŞTUR (opsiyonel)
- Büyük özellikler için `feature_request.yml` ile issue aç

### 3. UYGULA
- `database.py`: Yeni metot ekle
- `ui/`: Yeni sayfa veya mevcut sayfaya ekleme yap
- `tests/`: Yeni test ekle
- `main.py`: Menüye/gerekli yerlere bağla

### 4. TEST ET
```bash
python -m unittest discover -s tests -v
```

### 5. COMMIT & PUSH
```bash
git add <dosyalar>
git commit -m "feat: özellik açıklaması"
git push
```

## Kod Standartları
- CustomTkinter widget'ları kullan
- Türkçe label/buton metinleri
- `fg_color="#134e4a"` (teal) tema rengi
- Emoji ikonları test et (encoding)
