# Değişiklikler

## 0.11.0 — 2026-09-23

- Anakartın temsili çizimi; CPU soketi, VRM, çift RAM yuvası, M.2, PCIe, SATA, yonga seti ve bağlantı ayrıntılarıyla yeniden tasarlandı. Yedi temanın renklerine uyarlanır; gerçek pin/bağlantı planı değildir.
- Anakart izlerinde hareketli ışık, CPU çevresinde yumuşak vurgu ve grafikte yeni ölçüm halkası eklendi. Bunlar dekoratiftir; donanım devri ya da elektrik sinyali göstermez.
- Hareketler yalnızca görünürken çalışır; Ayarlar’daki **Arayüz animasyonları** kapatılınca durur. Görsel davranış testleri eklendi.

## 0.10.0 — 2026-09-23

- Doğrulanmış fan yardımcısı için etkin yerel oturumda şifresiz çalışma açıldı; fan modu değiştirmek artık yönetici onayı istemez.
- Etkin olmayan ve uzaktan oturumlar yetkisiz kalır. İzin yalnızca paketli yardımcıya aittir; anakart/kanal denetimi, güvenli eğri sınırları, yedekleme, geri okuma ve geri alma korunur.
- Bu yetki aynı oturumdaki başka yerel uygulamalardan yardımcı çağrıldığında da geçerlidir; genel root erişimi sağlamaz.

## 0.9.0 — 2026-09-23

- Tema seçimi her sayfada görünen sol menüye taşındı; Ayarlar seçimiyle eşzamanlı çalışır.
- Fan işlemleri için yalnızca paketli, kısıtlı yardımcıya ait kısa süreli yönetici yetkisi eklenerek ardışık mod değişikliklerinde tekrar şifre sorulması azaltıldı. İlk işlem yine yönetici onayı ister; yetki süresi dolunca tekrar sorulur.

## 0.8.0 — 2026-09-23

- Farklı ASUS anakartlarında mevcut Linux sensör, GPU, güç profili ve fan arayüzlerini otomatik gösteren destek tablosu eklendi. Doğrulanmamış modellerde izleme açık, fan yazma kapalıdır.
- Hazır fan eğrileri, yazma desteği olmasa da önizlenebilir; uygulama düğmesi yalnızca güvenli doğrulanmış kanallarda açılır.
- Bakır Kızılı, Mor Gece, Grafit ve Gün Işığı temaları eklendi; toplam yedi kalıcı tema var.
- Eksik CPU/bellek telemetrisi, sıfır toplam bellek/disk ve eksik çalışma süresi yüzünden oluşabilecek arayüz hataları giderildi.
- Doğrulanmış model adı tek başına fan yazımını açmaz; ASUS DMI üretici kimliği de şarttır.
- Yeni kapsam ve tema regresyon testleri eklendi.

## 0.7.0 — 2026-09-23

- Ayarlar bölümüne kalıcı Anvil Sarı, Gece Mavisi ve Orman Yeşili tema seçenekleri eklendi.
- Tema değişikliği kartlara, grafiklere, anakart çizimine ve fan/gösterge animasyonlarına anında uygulanır.
- KDE görev çubuğu ve masaüstü başlatıcısı için Anvil simgesi paketlendi.
- Doğrulanmış anakart fan kanalları için Sakin, Dengeli ve Yüksek soğutma hazır sıcaklık eğrileri eklendi; değişiklik mevcut ayrıcalıklı yardımcıdan ve geri okuma denetiminden geçer.

## 0.6.0 — 2026-09-22

- AMD ekran kartlarında `amdgpu` sysfs üzerinden kullanım, sıcaklık, güç, VRAM ve fan RPM ölçümleri eklendi; arayüzler yoksa değerler boş kalır. Gerçek AMD donanımında henüz sınanmadı.
- GPU fan devri RPM olarak gösterilir; RPM değeri yüzde gibi sunulmaz.
- Ana sayfada yalnızca dönen fanlar listelenerek panel sadeleştirildi.
- Fan kontrolü yalnızca eksiksiz PWM / PECI arayüzü olan doğrulanmış kanallarda açılır.
- Başarı bildirimi, ayrıcalıklı yardımcının eşleşen geri okuma yanıtı doğrulanınca gösterilir.

## 0.5.0 — 2026-09-22

- Gezinme yedi sayfadan beş bölüme sadeleştirildi; cihazlar ve tanılama birleştirildi.
- H610M-K'ya özgü bileşen çizimi, anakart bağımsız temsili şema oldu.
- ASUS kimliği DMI üretici bilgisinden algılanıyor; genel hwmon sensörleri korunuyor.
- Intel coretemp ve AMD k10temp / zenpower işlemci sıcaklıkları destekleniyor.
- Yazılabilir fan kontrolü yalnızca fiziksel olarak doğrulanmış anakart profiline bağlı.

## 0.4.0 — 2026-09-22

- H610M-K D4 / NCT6798 kanal 1 ve 2 için gerçek donanım fan kontrolü.
- Beş noktalı eğri, tam hız, root’a ait başlangıç yedeği ve geri dönüş.
- Sınırlı ayrıcalıklı yardımcı, girdi doğrulama ve yazma sonrası geri okuma.
- OpenRGB cihaz, renk ve efekt seçimi; Kingston Fury DDR4 algılaması.
- RPM içinde sürücü yükleme ayarı; GitHub kullanım ve katkı belgeleri.
- 0.3 sürümünün animasyon, uyarı, grafik ve sensör özellikleri dahil.

## 0.3.0 — 2026-09-21

- Doluluk çubuğu, sayfa geçişi, CPU şeması ve GPU fan simgesi animasyonları.
- Animasyonları kapatma seçeneği; gizli fan animasyonunda zamanlayıcı durdurulur.
- CPU/GPU/RAM grafik seçimi ve izlemeyi duraklatma.
- Sensör araması ve min/maks ölçümleri.
- VRAM takibi, ayarlanabilir sıcaklık uyarıları, oturum olay günlüğü.
- Eksik ölçümler grafikte boşluk olarak korunur.

## 0.2.0 — 2026-09-21

- Siyah-sarı tema ve daha okunaklı sans-serif yazı tipleri.
- Ana sayfada vektörel anakart şeması ve altında algılanan model adı.
- Fan durumu ve GPU fan yüzdesi ana sayfaya taşındı.
- Sensörlerin ayrıntıları ayrı sayfada korunuyor.
- Fan/RGB donanım yazma desteği bu alpha sürümünde mevcut değil.

## 0.1.0 — 2026-09-21

- CPU, NVIDIA GPU, bellek, disk ve hwmon izleme.
- Sistem güç profilleri, donanım envanteri, JSON/CSV dışa aktarımı.
