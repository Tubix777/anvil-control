# Anvil Control · 0.2.0 alpha

Fedora KDE üzerinde ASUS masaüstü bilgisayarlar için Türkçe, yerel Qt kontrol merkezi.
İlk test sistemi: ASUS PRIME H610M-K D4, i5-12400F, RTX 5060 Ti, Fedora 44 KDE.
Bağımsız bir projedir; ASUS ile bağlantılı değildir. Anvil geçici proje adıdır.

Siyah-sarı arayüz, ana sayfada özgün anakart şeması ve fan merkezi.
Şema temsili bir bileşen çizimidir; elektrik bağlantısı veya pin yerleşimi referansı değildir.
Yazı tipi: sistemde varsa Adwaita Sans, ardından Noto Sans / DejaVu Sans.

## Çalışan özellikler

- CPU sıcaklık ve kullanım grafiği, frekans, RAM ve kök dosya sistemi doluluğu.
- NVIDIA NVML üzerinden birinci GPU sıcaklığı, kullanım, güç ve fan yüzdesi.
- Kernel hwmon sensörleri ve fan/PWM arayüzlerinin tespiti.
- Sistemin D-Bus güç servisi üzerinden mevcut profilleri okuma ve değiştirme.
- Anakart, BIOS, işletim sistemi ve PCI sürücü envanteri.
- Yerel JSON tanılama ve CSV ölçüm dışa aktarımı.
- Yenileme aralığı, isteğe bağlı sistem tepsisi, 3.600 ölçümlük bellek geçmişi.

## Bilinen sınırlar

Fan eğrisi veya RGB donanım yazma desteği **yoktur**. Test sisteminde fan RPM/PWM
arayüzleri görünmüyor. Sürücü, kanal eşlemesi ve firmware geri dönüşü doğrulanmadan
fan kontrolü tamamlanmış sayılmaz. OpenRGB kuruluysa yalnızca ayrı uygulama açılır.
Eksik ölçümler sıfır yerine çizgi olarak gösterilir. Profil değişikliği sistemin
mevcut yetkilendirmesine bağlıdır; root olarak çalıştırmayın. Güç profilleri özel
fan eğrisi, overclock veya BIOS ayarı uygulamaz. NVIDIA telemetrisi isteğe bağlıdır;
AMD/Intel GPU telemetrisi ve çoklu GPU seçimi henüz yoktur. CPU sıcaklık özeti
Intel coretemp içindir; diğer sensörler sensör sayfasında görünür.

## Kaynaktan çalıştırma

Fedora bağımlılığı: `sudo dnf install python3-pyside6 pciutils`

Bu dizinde: `python3 -m anvil`

RPM: `sudo dnf install ./anvil-control-0.2.0-1.fc44.noarch.rpm`

RPM kurulduğunda uygulama menüsünden **Anvil Control** açılabilir.
Kaldırma: `sudo dnf remove anvil-control`.

## Doğrulama

`python3 -m unittest discover -s tests -v`

`QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 tests/smoke_ui.py`

İkinci test gerçek sistemde salt okunur ölçümler, yedi sayfa ve JSON/CSV dışa
aktarımını denetler. H610M-K D4 test makinesine özgüdür. Güç değiştirme adaptörü
birim testlerinde taklit edilir; otomatik testler güç profilini değiştirmez.

## Yayın durumu

Deneysel alpha; Fedora tarafından onaylanmış bir paket değildir. RPM imzasızdır.
Kararlı sürüm öncesinde gerçek profil geçişi/yetkilendirme, farklı cihaz ve
masaüstleri, paket politikaları ve fan desteği ayrıca doğrulanmalıdır.

Kaynak kodu: https://github.com/Tubix777/anvil-control

İndirilebilir sürümler: https://github.com/Tubix777/anvil-control/releases

## Teknik kaynaklar

- https://www.asus.com/au/motherboards-components/motherboards/prime/prime-h610m-k-d4/techspec/
- https://www.kernel.org/doc/html/latest/hwmon/nct6775.html
- https://docs.nvidia.com/deploy/nvml-api/

Telemetri `/proc`, `/sys` ve NVML üzerinden okunur. Güç profili değişikliği yalnızca
kullanıcı düğmeye bastığında D-Bus üzerinden istenir ve sonuç tekrar okunur.
Ağ çağrısı, otomatik rapor gönderimi, sürücü kurulumu veya BIOS değişikliği yoktur.
