# Değişiklikler

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
