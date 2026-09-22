# ANVIL CONTROL

**ASUS sistemleri için Fedora’da yerel donanım kontrolü.** Anakart ve Linux’un sunduğu özellikler otomatik algılanır; desteklenmeyen donanıma ayar yazılmaz.

[![Release](https://img.shields.io/github/v/release/Tubix777/anvil-control?include_prereleases&color=ffd438)](https://github.com/Tubix777/anvil-control/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

[İndir](https://github.com/Tubix777/anvil-control/releases) · [Değişiklikler](CHANGELOG.md) · [Hata bildir](https://github.com/Tubix777/anvil-control/issues/new/choose) · [Katkı](CONTRIBUTING.md)

![Anvil Control ana sayfa](docs/overview.png)

## Donanım kapsamı

Anvil, anakart modelini DMI’dan okur ve Linux’un sunduğu sıcaklık, fan ve güç arayüzlerini gösterir. Intel `coretemp` ile AMD `k10temp` / `zenpower` işlemci sıcaklıkları okunur. NVIDIA GPU ölçümleri NVML’ye, RGB cihazları isteğe bağlı OpenRGB’ye bağlıdır. Mevcut aygıta göre bazı değerler gösterilmeyebilir.

| Özellik | Kapsam |
| --- | --- |
| Anakart, sensör, fan devri ve güç profilleri | Linux sürücüsü / servisinin sunduğu arayüzler |
| Grafik, RAM ve depolama | Genel Linux ölçümleri |
| NVIDIA GPU | İsteğe bağlı NVML sürücüsü |
| RGB | OpenRGB’nin algıladığı aygıt ve modlar |
| Yazılabilir anakart fan eğrisi | Şimdilik yalnızca aşağıdaki, fiziksel olarak doğrulanmış H610M-K D4 profili |

Bu nedenle uygulama farklı ASUS sistemlerinde genel izleme için kullanılabilir; her modelde aynı sensörler veya yazılabilir fan kontrolü olduğu iddia edilmez. Yeni bir fan profili ancak anakart, kontrolcü, kanal ve sıcaklık kaynağı gerçek donanımda doğrulandıktan sonra eklenir.

## Kurulum — Fedora 44 KDE

[Sürümlerden](https://github.com/Tubix777/anvil-control/releases) RPM’yi indirin:

```bash
sudo dnf install ./anvil-control-0.5.0-1.fc44.noarch.rpm
anvil-control
```

Uygulama menüsünden **Anvil Control** olarak da açılabilir. RPM, kernel sensör sürücüsünü sonraki açılışlarda yüklemek üzere ayarlar. RGB için isteğe bağlı `sudo dnf install openrgb` kurun, ardından **Cihazlar → Cihazları tara** yolunu kullanın. GUI’yi root olarak çalıştırmayın; fan değişikliklerinde sistem kimlik doğrulaması gerekir.

Kaldırma: `sudo dnf remove anvil-control`. Paketi kaldırmadan önce fan ayarı değiştirdiyseniz **Önceki ayarlar** düğmesiyle başlangıç eğrisini geri yükleyin.

## Arayüz

Beş bölüm: **Genel bakış**, **Sensörler**, **Güç**, **Cihazlar** (RGB, envanter ve tanılama) ve **Ayarlar**. Ana sayfada canlı ölçümler ve fan paneli; ayrıntılarda arama, grafikler, CSV ölçümleri ve isteğe bağlı JSON tanılama bulunur. Veriler yerelde kalır; kendiliğinden gönderilmez.

## Doğrulanmış fan desteği

Fedora 44 KDE üzerinde **ASUS PRIME H610M-K D4 / NCT6798**, kanal 1 ve 2 için eğri yazma, tam hız, geri okuma ve önceki ayarlara dönüş gerçek donanımda test edildi. Tam hız denemesinde yaklaşık 700 → 1.724 RPM ve 1.830 → 3.154 RPM okundu; testten sonra başlangıç ayarları geri yüklendi.

Yazma profili kesin anakart adına ve NCT6798’e kilitlidir. Yalnızca PWM, PECI sıcaklık kaynağı, sınırlı sıcaklık/devir aralığı ve güvenli eğri kabul edilir. Son iki eğri noktası %100 olmalıdır; fan durdurma veya düşük sabit hız yoktur. Donanım eğriyi uygular; uygulamanın açık kalması gerekmez. Yedek root’a ait `/run/anvil-control` altında tutulur ve yeniden başlatmada silinir. Kanal numarası kasadaki CPU / SYS etiketini garanti etmez.

Başka ASUS modellerinde sensörler görünse dahi fan ayarı yazımı kapalıdır; o kart henüz doğrulanmamıştır.

## Test ve sınırlar

```bash
python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 tests/smoke_ui.py
```

20 birim testi; gerçek sensör telemetrisiyle beş bölümlü arayüz testi. Smoke testi yalnızca mevcut sistemde çalışır. Bu bağımsız alpha proje ASUS/Fedora tarafından onaylanmamıştır. Anakart çizimi temsili şemadır, pin bağlantısı değildir. NVIDIA dışı GPU telemetrisi şu an yoktur. JSON tanılama raporunu paylaşmadan önce içeriğini inceleyin; raporda kart/BIOS, PCI ve sensör bilgileri bulunur.

## English

Local Fedora hardware monitoring and controls for ASUS systems. Board identity and available Linux sensor interfaces are discovered dynamically. Writable motherboard fan curves remain restricted to the physically validated PRIME H610M-K D4 / NCT6798 profile; monitoring may work on other ASUS boards without fan-write support. Experimental alpha.

## Kaynaklar

- [Linux NCT6775/NCT6798 hwmon sürücüsü](https://www.kernel.org/doc/html/latest/hwmon/nct6775.html)
- [ASUS PRIME H610M-K D4 özellikleri](https://www.asus.com/au/motherboards-components/motherboards/prime/prime-h610m-k-d4/techspec/)
- [NVIDIA NVML](https://docs.nvidia.com/deploy/nvml-api/) · [OpenRGB](https://openrgb.org/)
