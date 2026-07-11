# 💎 FINEding — Akıllı Kişisel Finans Yönetimi

<div align="center">

**Python + CustomTkinter ile geliştirilmiş, şık ve güçlü bir masaüstü finans takip uygulaması.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-17%2F17%20✅-green)](tests/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/iefeozdingis/FINEding)](https://github.com/iefeozdingis/FINEding/issues)

</div>

---

## 🎯 Neden FINEding?

Harcamalarını kontrol etmek, bütçeni yönetmek ve finansal hedeflerine ulaşmak ister misin?  
FINEding, tüm gelir-gider takibini **tek bir şık arayüzde**, **ücretsiz** ve **reklamsız** olarak sunar.

> 💡 *"Paranı yönet, hayatını yönet."*

---

## ✨ Tüm Özellikler

### 📊 Dashboard
- **4 özet kartı**: Toplam Gelir, Gider, Bakiye, İşlem Sayısı
- **Bütçe ilerleme çubukları**: Kategori bazlı renkli progress bar (🟢🟡🔴)
- **Akıllı uyarılar**: Bütçe aşımı ve yaklaşan limit bildirimleri
- **Hızlı işlem**: 💰 +Gelir / 💸 +Gider popup (tutar yaz, Enter'la)
- **Günlük/Haftalık filtre**: "Bugün", "Bu Hafta", "Tümü" butonları
- **Arama & filtreleme**: Kategori, açıklama, etiket veya tutara göre anlık arama
- **🔍 Global arama**: Ctrl+F ile tüm işlem ve borç/alacaklarda anında ara
- **Dışa aktar**: Tek tıkla CSV 📄, Excel 📗, PDF 📕
- **📥 İçe aktar**: CSV veya Excel dosyasından toplu işlem yükle

### 💰 Gelir & Gider Yönetimi
- Gelir/gider kaydı ekle, düzenle, sil, geri al
- Kategori bazlı işlem takibi (özel kategori eklenebilir)
- 🏷️ İşlemlere serbest etiket ekleme (virgülle ayrılmış), etikete göre arama
- Toplu silme (Ctrl+seçim)
- Tarih otomatik formatlama (GG.AA.YYYY)

### 📅 Bütçe & Planlama
- **Aylık bütçe**: Kategori başına limit belirle
- **Bütçe ilerleme çubukları**: Dashboard'da görsel takip
- **Aylık planlama**: Gelecek ay gelir/gider tahmini
- **Borç & Alacak takibi**: Kimden, ne kadar, vadesi ne zaman?
- **🔄 Tekrarlayan işlemler**: Kira, fatura gibi düzenli ödemeleri her ay otomatik ekler
- **🎯 Tasarruf hedefleri**: Hedef tutar/tarih belirle, katkı ekle, renkli ilerleme çubuğuyla takip et

### 📈 Grafikler & Analiz
- **Aylık gelir/gider çubuk grafiği**
- **Kategori dağılımı pasta grafikleri** (Gelir + Gider)
- **📊 Bu Ay vs Geçen Ay** karşılaştırma grafiği
- **📆 Yıllık Karşılaştırma** — yıl bazında gelir/gider trendi
- Matplotlib ile profesyonel görselleştirme

### 🔐 Çok Kullanıcılı Sistem
- Her kullanıcı kendi hesabıyla giriş yapar
- **Admin paneli**: Kullanıcı yönetimi, şifre sıfırlama, kullanıcı silme
- Şifreler SHA-256 + salt ile hash'lenir
- "Beni Hatırla" özelliği

### 🎨 Arayüz
- **🌓 Aydınlık/Karanlık tema**: Sidebar'dan tek tıkla değiştir
- CustomTkinter ile modern, responsive tasarım
- Teal ( #0f766e ) renk teması
- Klavye kısayolları (Ctrl+D Dashboard, Ctrl+N Gelir, vb.)
- Emoji ikonları ile zengin görsel deneyim

### 🛡️ Sistem Özellikleri
- **🔔 Masaüstü bildirimleri**: Borç vadesi yaklaşınca uyarı
- **⬇️ Sistem tepsisi**: Kapatınca arka planda çalışır
- **💾 Otomatik yedekleme**: Uygulama kapanırken `backups/` altına yedekler (son 10 tutulur)
- **🗂 Manuel yedekleme**: İstediğin zaman yedek al, geri yükle
- SHA-256 checksum ile yedek bütünlük kontrolü

---

## 🚀 Hızlı Başlangıç

### Gereksinimler
- **Python 3.10+** ([python.org](https://python.org))
- **Windows 10/11**

### Tek Tıkla Kurulum (Yeni Kullanıcılar)
```bash
# Projeyi indir, KURULUM.bat'a çift tıkla — her şeyi otomatik yapar!
```

### ⚡ Tek Dosya İndir (En Kolay)
**[📥 FINEding.exe İndir](https://github.com/iefeozdingis/FINEding/releases/latest)**  
Python kurmaya gerek yok! Tek `.exe` dosyası, çift tıkla çalışır (~216 MB).

### Manuel Kurulum
```bash
git clone https://github.com/iefeozdingis/FINEding.git
cd FINEding
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Varsayılan Giriş
| Kullanıcı | Şifre |
|-----------|-------|
| `admin` | `12345` |

---

## ⌨️ Klavye Kısayolları

| Kısayol | Sayfa |
|---------|-------|
| `Ctrl+F` | 🔍 Tüm Uygulamada Ara |
| `Ctrl+D` | Dashboard |
| `Ctrl+N` | Gelir Ekle |
| `Ctrl+Shift+N` | Gider Ekle |
| `Ctrl+Shift+G` | Grafikler |
| `Ctrl+B` | Bütçe |
| `Ctrl+P` | Planlama |
| `Ctrl+,` | Ayarlar |
| `Ctrl+Q` | Çıkış |

---

## 🧪 Testler

```bash
python -m unittest discover -s tests -v
```

```
✅ test_aylik_karsilastirma
✅ test_bcrypt_hash
✅ test_borclar
✅ test_budget_status_summary
✅ test_etiket
✅ test_gunluk_haftalik
✅ test_import_csv
✅ test_import_excel
✅ test_islem_log
✅ test_planlama
✅ test_search
✅ test_tasarruf_hedefi
✅ test_tekrarlayan
✅ test_transaction_update_budget_and_settings
✅ test_undo
✅ test_user_authentication
✅ test_yillik_karsilastirma
─────────────────────────
17 tests — ALL OK
```

---

## 🗂 Proje Yapısı

```
FINEding/
├── main.py              # Uygulama ana giriş + tema + menü
├── database.py           # SQLite veritabanı katmanı
├── requirements.txt      # Bağımlılıklar
├── KURULUM.bat           # 🆕 Tek tıkla kurulum
├── run_finans_defterim.bat  # Başlatıcı
├── ui/
│   ├── dashboard.py      # Ana dashboard (kartlar + tablo + filtre + ihracat)
│   ├── gelir.py          # Gelir ekleme sayfası
│   ├── gider.py          # Gider ekleme sayfası
│   ├── butce.py          # Bütçe yönetimi
│   ├── planlama.py       # Planlama + borç/alacak + tekrarlayan işlemler
│   ├── grafikler.py      # Grafikler ve aylık karşılaştırma
│   ├── raporlar.py       # Rapor/dışa aktarım (yedek)
│   ├── ayarlar.py        # Ayarlar + admin paneli
│   ├── giris.py          # Giriş/kayıt ekranı
│   ├── hakkinda.py       # Hakkında sayfası
│   └── utils.py          # Tarih/para formatlama yardımcıları
├── tests/
│   └── test_database.py  # 7 birim testi
├── database/             # SQLite veritabanı
├── backups/              # Otomatik yedekler
├── logs/                 # Uygulama logları
└── assets/               # İkon ve tema dosyaları
```

---

## 🛠 Teknoloji Stack'i

| Katman | Teknoloji |
|--------|----------|
| Arayüz | CustomTkinter |
| Grafik | Matplotlib |
| Veritabanı | SQLite3 |
| Rapor | ReportLab (PDF), openpyxl (Excel) |
| Bildirim | Plyer |
| Sistem Tepsisi | Pystray |

---

## 🩹 Son Düzeltmeler (2026-07-10)

- **Planlama → Tekrarlayan sekmesi açılmıyordu:** `_tekrarlayan_olustur` ve ilgili metodlar yanlışlıkla `BorcDuzenlePenceresi` sınıfının altına yazılmıştı; doğru sınıfa (`PlanlamaSayfasi`) taşındı.
- **Bütçe sayfası tema hatası:** `assets/fineding_theme.json` içindeki `CTkTextbox` bölümünde `border_color` anahtarı eksikti, eklendi.
- Tüm sayfalar (`ButceSayfasi`, `PlanlamaSayfasi`, `HakkindaSayfasi`) artık hatasız açılıyor; 12/12 test yeşil.

## 📝 Geliştirici Notları

- **Commit Convention:** `fix:`, `feat:`, `chore:`, `style:`, `test:`
- **Issue sistemi:** Bug bildirimi ve özellik isteği şablonları mevcut
- **CI/CD:** GitHub Actions ile otomatik test + lint
- **Auto-issue:** CI başarısız olursa otomatik bug issue'su oluşturur

---

## 📄 Lisans

MIT — Dilediğin gibi kullan, değiştir, paylaş.

---

<div align="center">

**⭐ Bu projeyi beğendiysen yıldız vermeyi unutma!**

[![Star History Chart](https://img.shields.io/github/stars/iefeozdingis/FINEding?style=social)](https://github.com/iefeozdingis/FINEding)

</div>

### Tek Tıkla Çalıştırma
`run_finans_defterim.bat` dosyasına çift tıklayarak uygulamayı doğrudan başlatabilirsin.

---

## 🎯 İlk Kullanım

1. Uygulama ilk açıldığında giriş ekranı gelir
2. **"📝 Yeni Hesap Oluştur"** butonuna tıkla
3. Ad soyad, kullanıcı adı ve şifreni belirle
4. **İlk oluşturulan hesap otomatik olarak 👑 Admin olur**
5. Giriş yap ve kullanmaya başla!

> ℹ️ Veritabanı dosyası (`database/finans.db`) `.gitignore`'a eklenmiştir.  
> GitHub'dan indiren herkes sıfırdan kendi hesabını oluşturur.

---

## 👑 Admin Özellikleri

İlk kayıt olan kullanıcı (ID: 1) admin yetkilerine sahiptir:

- **Kullanıcı Listesi**: Tüm kayıtlı kullanıcıları görüntüle
- **Şifre Sıfırlama**: Herhangi bir kullanıcının şifresini değiştir
- **Kullanıcı Silme**: İstenmeyen hesapları kalıcı olarak sil

Admin paneline **Ayarlar** sayfasının en altından ulaşılır.

---

## 🛠 Teknoloji

| Teknoloji | Kullanım |
|---|---|
| Python 3.10+ | Ana dil |
| CustomTkinter | Modern masaüstü arayüzü |
| SQLite3 | Yerel veritabanı |
| Matplotlib | Grafik ve görselleştirme |
| Pillow (PIL) | Görüntü işleme |
| Plyer | Masaüstü bildirimleri |
| PyStray | Sistem tepsisi entegrasyonu |
| OpenPyXL | Excel dışa aktarım |
| ReportLab | PDF dışa aktarım |

---

## 📁 Proje Yapısı

```
FINEding/
├── main.py              # Uygulama giriş noktası
├── database.py          # Veritabanı işlemleri
├── requirements.txt     # Python bağımlılıkları
├── run_finans_defterim.bat  # Tek tıkla başlatma
├── run_finans_defterim.vbs  # Sessiz başlatma
├── assets/              # Logo ve tema dosyaları
├── database/            # SQLite veritabanı (.gitignore)
├── exports/             # Dışa aktarılan raporlar
├── logs/                # Uygulama logları
├── tests/               # Test dosyaları
└── ui/                  # Arayüz modülleri
    ├── dashboard.py     # Ana gösterge paneli
    ├── gelir.py         # Gelir ekleme sayfası
    ├── gider.py         # Gider ekleme sayfası
    ├── giris.py         # Giriş ekranı
    ├── grafikler.py     # Grafikler sayfası
    ├── butce.py         # Bütçe yönetimi
    ├── planlama.py      # Planlama & borç takibi
    ├── raporlar.py      # Rapor dışa aktarım
    ├── ayarlar.py       # Ayarlar & admin paneli
    ├── hakkinda.py      # Hakkında sayfası
    └── utils.py         # Yardımcı fonksiyonlar
```

---

## 🧪 Test

```bash
python -m unittest discover -s tests -v
```

---

## 📝 Lisans

MIT License — Dilediğin gibi kullan, değiştir, paylaş.

---

**FINEding** — Finansal geleceğini planla, kontrol et! 💎
