# Değişiklik Günlüğü

Tüm önemli değişiklikler bu dosyada tutulur. Biçim [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/)
esas alır; sürümleme [Semantic Versioning](https://semver.org/lang/tr/).

## [1.10.0] - 2026-07-28

Otomatik kategori önerisi (#14). Test sayısı 132 → 140.

### Eklendi

- **Otomatik kategori önerisi.** İşlem eklerken açıklama alanına yazıldıkça,
  geçmiş işlemlerde aynı/benzer açıklamaya en çok atanan kategori bir öneri
  olarak gösterilir; tıklayınca kategori alanına uygulanır. Basit keyword
  eşleştirme (LIKE) — ML gerektirmez, tek sorgu. Beraberlikte en son
  kullanılan kategori kazanır; öneri türe (Gelir/Gider) ve kullanıcıya
  özeldir (başka kullanıcının verisi sızmaz).

## [1.9.0] - 2026-07-23

Çoklu para birimi desteği (#15). Test sayısı 117 → 132.

### Eklendi

- **Çoklu para birimi (TRY, USD, EUR, GBP).** İşlem eklerken/düzenlerken para
  birimi seçilebilir; TCMB günlük kuruyla (veya elle girilen kurla) TL
  karşılığı hesaplanıp dashboard'da hem orijinal hem TL gösterilir. Depolama:
  `tutar` TL-kuruş (temel/raporlama) olarak saklanır, orijinal tutar + birim
  ayrıca korunur — böylece bakiye/bütçe/rapor TL bazında değişmeden doğru
  kalır. Kur kaynağı TCMB `today.xml` (ForexSelling): **Ayarlar ▸ Döviz
  Kurları**'ndan güncellenir ya da elle girilir, ayrıca günde bir arka planda
  sessizce tazelenir (çevrimdışıysa son kur/elle kur kullanılır). Ağ çekimi
  worker thread'de, DB yazımı ana thread'de; yeni bağımlılık yok (urllib +
  xml.etree). v8 migrasyonu eski işlemleri TRY kabul eder.

## [1.8.0] - 2026-07-23

Para artık kuruş bazlı tam sayı saklanıyor. Test sayısı 107 → 117.

### Değişti

- **Para birimi tam sayı kuruşa taşındı (v7 migrasyonu).** Tüm tutar
  sütunları (`islemler`, `butceler`, `planlanan`, `borclar`, `tekrarlayan`,
  `borc_odemeler`, `tasarruf_hedefleri`) `REAL`(lira) yerine artık
  `INTEGER`(kuruş) — 1 TL = 100. Float saklama `0.1 + 0.2 =
  0.30000000000000004` sınıfı birikimli yuvarlama hatalarına ve çok satırlı
  `SUM` kaymasına açıktı; tam sayı kuruş depolamayı ve toplamayı **tam
  kesin** yapar. Eski (REAL/lira) veritabanları açılışta otomatik ve kayıpsız
  çevrilir. Arayüz sözleşmesi değişmez: DB sınırında lira'ya çevrildiği için
  ekranlar, içe/dışa aktarım ve tüm hesaplamalar aynı çalışır. Bu, çoklu para
  birimi (her biri minör birimde tam sayı) için de zemin hazırlar.

## [1.7.0] - 2026-07-22

Kapsamlı bir denetim ve sağlamlaştırma turu. Test sayısı 61 → 107.

### Kritik

- **Paketlenmiş uygulamada veri kaybı giderildi.** PyInstaller onefile'da
  `__file__` geçici `_MEIxxxx` klasörünü gösterdiği için veritabanı, loglar
  ve yedekler her çalıştırmada silinen geçici klasöre yazılıyordu — exe
  üzerinden girilen her şey kapanışta kayboluyordu. Yollar artık
  `sys.executable` yanına (kalıcı) sabitlendi.
- **Borç/alacak muhasebesi düzeltildi (model B).** Borç/alacak ayrı bir
  bilanço kalemi; ödeme artık varsayılan olarak ana bakiyeye/gelir-gidere
  dokunmuyor. Önceki asimetri (açılış bakiyeye yansımıyor ama ödeme
  yansıyor) alacak-tahsilat şişmesine ve kredili alışverişte çift sayıma yol
  açıyordu. Net pozisyon ayrı panelde. (v5 migrasyonu eski türev kayıtları
  temizler; ödeme geçmişi korunur.)

### Güvenlik

- Zayıf şifre yolu kaldırıldı: bcrypt yoksa artık sessizce tuzsuz SHA-256
  üretilmiyor, hata veriliyor. Eski hash'ler girişte bcrypt'e yükseltilir.
- Yedek imzalama anahtarı üretilemezse sabit gömülü anahtara düşmüyor
  (kurcalama tespitini etkisiz kılıyordu).
- Geri yüklemede eski veritabanı düz metin `.restore-bak` olarak
  bırakılmıyor; başarılı geri yüklemeden sonra siliniyor.
- Özel kategoriler artık kullanıcıya özel — kullanıcılar arası sızmıyor.
- Kaba kuvvet giriş sayacı kalıcı ve ana thread'i bloklamıyor.

### Düzeltmeler

- Dışa aktarma (CSV/Excel/PDF) worker thread'de ana-thread SQLite
  bağlantısını kullandığı için hiç çalışmıyordu — düzeltildi.
- İçe aktarma büyük dosyalarda arayüzü donduruyordu — ayrıştırma worker
  thread'e alındı, DB yazma ana thread'de kaldı.
- Toplu silme sonrası geri-al yalnızca son kaydı döndürüyordu; artık parti
  yığını ile hepsi geri alınabiliyor.
- Kalanı aşan borç ödemesi bakiyeden fazla düşüyordu — kırpılıyor.
- Plan kopyalama atomik DB metoduna taşındı (çökme anında veri kaybı yok).
- Yeni tekrarlayan kural geriye dönük bu ayı eklemiyor (çift kayıt yok).
- Şifre değiştirmede yanlış mevcut şifre giriş kilidini beslemiyor.
- `borc_odemeler` → `borclar` FK cascade eklendi (yetim kayıt yok).
- Grafik aylık çubuklar kronolojik sıraya alındı; dashboard tablosu artık
  biçimli tutar/tarih gösteriyor; içe aktarım Türk binlik ayracını doğru
  okuyor; çok-adımlı yazma yolları atomik transaction'a alındı.

### Altyapı & Dokümantasyon

- CI: mypy modüller arası tip denetimi (`follow_imports=normal`), asgari
  test-sayısı kapısı, `types-PyYAML`. LICENSE dosyası eklendi. README
  temizlendi ve İngilizce özet eklendi. CHANGELOG/CONTRIBUTING/SECURITY
  eklendi. Sürüm tek kaynaktan (`version.py`).

## [1.6.2] - 2026-07-12

- Eski (bcrypt öncesi) SHA-256 şifreler için ayrı doğrulama yolu.
- Manuel yedekte WAL checkpoint zorlanması (veri kaybını önler).
- "Geri Al" artık etiketleri koruyor.
- Tepsi simgesi yoksa uygulama gerçekten kapanıyor.
- Tema tercihi kalıcı; admin şifre sıfırlamada yeni şifre maskeli.

## [1.6.1] - 2026-07-12

- Kritik yedekleme düzeltmesi.

## [1.6.0] - 2026-07-12

- bcrypt şifre hash'leme, HMAC yedek bütünlüğü, çok kullanıcılı sistem.

## [1.0.1] - 2026-07-08

- Hata düzeltmeleri ve kararlılık güncellemeleri.

[1.10.0]: https://github.com/iefeozdingis/FINEding/releases/tag/v1.10.0
[1.9.0]: https://github.com/iefeozdingis/FINEding/releases/tag/v1.9.0
[1.8.0]: https://github.com/iefeozdingis/FINEding/releases/tag/v1.8.0
[1.7.0]: https://github.com/iefeozdingis/FINEding/releases/tag/v1.7.0
[1.6.2]: https://github.com/iefeozdingis/FINEding/releases/tag/v1.6.2
[1.6.1]: https://github.com/iefeozdingis/FINEding/releases/tag/v1.6.1
[1.6.0]: https://github.com/iefeozdingis/FINEding/releases/tag/v1.6.0
[1.0.1]: https://github.com/iefeozdingis/FINEding/releases/tag/v1.0.1
