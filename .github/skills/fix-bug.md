---
name: fix-bug
description: Hata tespit edildiğinde uygulanacak workflow. Kullanıcı bir hata bildirdiğinde veya sen bir hata bulduğunda tetiklenir.
---

# 🐛 Hata Düzeltme Workflow'u

## Süreç (Sırayla uygula)

### 1. HATAYI ANLA
- Kullanıcının ne dediğini dikkatlice oku
- Hatanın hangi dosyada/dosyalarda olduğunu tespit et
- İlgili kodları oku

### 2. ISSUE OLUŞTUR
- GitHub'da `bug_report.yml` şablonuyla issue aç
- Başlık: `[BUG] kısa açıklama`
- İçerik: Hata açıklaması, tekrarlama adımları, beklenen davranış
- Browser otomasyonu ile `issues/new?template=bug_report.yml` kullan

### 3. DÜZELT
- Kök nedeni bul
- Minimal değişiklik yap
- Yan etkileri kontrol et
- `pylanceFileSyntaxErrors` ile syntax kontrolü yap

### 4. TEST ET
```bash
python -m unittest discover -s tests -v
```
- 7 testin hepsi geçmeli
- Gerekirse yeni test ekle

### 5. COMMIT & PUSH
```bash
git add <dosyalar>
git commit -m "fix: kısa açıklama" -m "- detay 1 - detay 2"
git push
```

### 6. ISSUE'YU KAPAT
- Commit hash'ini referans göster
- Yorum: "✅ Düzeltildi — Commit XXXXX"
- `Close with comment` yap

## Doğrulama (Verification)
- [ ] Syntax hatası yok
- [ ] Testler geçiyor (7/7)
- [ ] Issue oluşturuldu
- [ ] Commit push'landı
- [ ] Issue kapatıldı
