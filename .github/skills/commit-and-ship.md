---
name: commit-and-ship
description: Değişiklikleri commit'leme ve yayınlama workflow'u.
---

# 🚀 Commit & Ship Workflow'u

## Convention
```
<type>: <Türkçe kısa açıklama>

- detay 1
- detay 2
```

## Type'lar
| Type | Kullanım |
|------|----------|
| `fix:` | Hata düzeltme |
| `feat:` | Yeni özellik |
| `chore:` | Bakım, yapılandırma |
| `style:` | Kod formatı (black, isort) |
| `test:` | Test ekleme/güncelleme |
| `docs:` | Dokümantasyon |

## Süreç
1. `git status` ile değişiklikleri kontrol et
2. Sadece anlamlı dosyaları ekle (`git add`)
3. `git diff --staged` (opsiyonel kontrol)
4. Commit
5. Push

## Anti-Pattern'ler
| Yapma | Yap |
|-------|-----|
| `git add .` | `git add <spesifik dosyalar>` |
| `git commit -m "fix"` | Açıklayıcı commit mesajı |
| Push'u unut | Her commit'ten sonra push |
| Debug dosyalarını commit'le | `.gitignore`'a ekle, sil |
