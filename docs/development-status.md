# Geliştirme durumu

## 2026-10-06 — 0.14.0 hazırlığı

Kullanıcının hedefi: fan yönetimi, sade ana ekran ve özellikle Fedora dışındaki
Linux dağıtımlarında kurulabilen paketler. Kullanıcı açıkça dur diyene kadar
geliştirme devam edecek. Otuz dakikalık mevcut yinelenen görev etkinleştirildi.

Aktif checkout: bu belgenin bulunduğu çalışma ağacı. Önce `AGENTS.md`, güncel
kullanıcı mesajları ve `git status` okunmalı. Eski `publish-base` checkout'undaki
tamamlanmamış Debian değişiklikleri korunuyor; güncel geliştirme burada sürüyor.

Planlanan ilk kapsam:

- Fedora RPM'nin mevcut sınırlı kontrol davranışını korumak.
- Debian/Ubuntu için izleme paketi, sistem Qt'si eksik olan dağıtımlar için kendi
  Qt bağımlılıklarını taşıyan çevrimdışı taşınabilir paket hazırlamak.
- Paketleri temiz geçici ortamda kurup gerçek arayüz oluşturulmasıyla sınamak.
  Türev dağıtımların sonucunu Ubuntu/Debian testlerinden varsaymamak.
- Ana ekranın teknik fan ayrıntılarını isteğe bağlı açılır hale getirmek.
- Aynı fan eğrisinin tekrar uygulanmasındaki gereksiz tam hız geçişini gidermek;
  gerçek değişikliklerde geri okuma, yedekleme ve geri alma davranışını korumak.
- Fanın durup tekrar dönme okumalarını ve denetleyici tepki sürelerini göstermek.

Bu çalışma sırasında canlı fan, güç veya RGB ayarı değiştirilmedi. Yerel sistem
paketi kurulmadı. Denenmeyen kartlarda yazma kısıtları kaldırılmayacak.

## Doğrulama ve yayın

98 birim testi ve Fedora üzerindeki salt okunur arayüz testi geçti. Son kaynak
paketleri Ubuntu 22.04/24.04, Debian 13, Ubuntu 26.04, Deepin 25 ve Arch Linux'ta
normal kullanıcıyla kuruldu/açıldı; ekransız ve sanal X11 kontrolleri geçti.
Taşınabilir arşiv ayrıca temiz Fedora 44 konteynerinde aynı iki açılış testini
geçti. Son wheel Ubuntu 24.04'te çevrimdışı özel venv kurulumu ve X11 testini geçti;
11 modülün kaynakla birebir eşleştiği ve bağımlılık bütünlüğü doğrulandı.

0.14.0 alpha kaynak ve sürümlü Fedora RPM, iki DEB, taşınabilir arşiv ve wheel
ile GitHub'da yayımlanmak üzere hazırlanıyor. CI sekiz dağıtım/paket hedefini
tekrar sınayacak; yerel sonuçlar ve CI sonuçları birbirine karıştırılmamalı.

Sonraki çalışmanın öncelikleri:

1. GitHub sürümünün tüm dosyalarının yüklenmesini ve CI sonuçlarını kontrol et.
   Bu yayın tamamlanmadan yeni sürüm numarası üretme.
2. Ayrı Zorin ortamı kurup gerçek dağıtım sonucu elde et; Ubuntu tabanını yalnız
   kurulum hedefi olarak kullan. Wayland açılışı ve masaüstü menüsü de sınanmalı.
3. DEB güncelleme/kaldırma ve bozuk/yarım özel Qt ortamından kurtarma senaryolarını
   incele; kullanıcı verilerini koru.
4. Fan kanalı adları için kullanıcı etiketleri ve denetleyici tepki süreleri için
   doğrulanabilir ayar tasarımı geliştir. Bugünkü düzeltme aynı ayarı yeniden
   yazmanın hız darbesini giderir; BIOS kaynaklı dalgalanmanın sebebi ve çözümü
   henüz kanıtlanmadı. Canlı donanım ayarlarını kendiliğinden değiştirme.

Geliştirme durdurulmadı; açık kullanıcı durma talimatı gelene kadar yinelenen
görev bu hedeflerle devam eder.
