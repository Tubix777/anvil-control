# ANVIL CONTROL

**ASUS masaüstün için siyah-sarı, yerel Fedora kontrol merkezi.**

[![Release](https://img.shields.io/github/v/release/Tubix777/anvil-control?include_prereleases&color=ffd438)](https://github.com/Tubix777/anvil-control/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

[İndir](https://github.com/Tubix777/anvil-control/releases) · [Değişiklikler](CHANGELOG.md) · [Hata bildir](https://github.com/Tubix777/anvil-control/issues/new/choose) · [Katkı](CONTRIBUTING.md)

![Anvil Control ana sayfa](docs/overview.png)

## 0.4.0 ile gerçek fan kontrolü

PRIME H610M-K D4 üzerindeki **NCT6798** denetleyicisine erişim sağlanır.
Ana sayfadan kanal seçerek beş noktalı otomatik eğri, tam hız ve önceki ayarlara
geri dönüş kullanılabilir. Eğriyi donanım yürütür; uygulamanın açık kalması gerekmez.

| Özellik | Durum |
| --- | --- |
| H610M-K D4, fan kanal 1 / 2 | Eğri, tam hız, geri dönüş gerçek donanımda test edildi |
| CPU, RAM, SSD ve NVIDIA GPU izleme | Canlı veriler, VRAM, grafikler ve sensör min/maks |
| Güç profilleri | Sistemin D-Bus servisi üzerinden okuma/yazma |
| RGB renk ve efekt | OpenRGB’nin algıladığı cihaz ve modlarla sınırlı |
| Kingston Fury DDR4 RGB | Algılandı; renk komutu tamamlandı, fiziksel renk görsel olarak doğrulanmadı |
| Anakart RGB başlığı | Bu test sisteminde OpenRGB tarafından algılanmadı |
| Diğer anakartlarda fan yazma | Etkin değil; model ve kanal kısıtlaması var |

## Kurulum — Fedora 44 KDE

[Sürümlerden](https://github.com/Tubix777/anvil-control/releases) RPM dosyasını indirin:

```bash
sudo dnf install ./anvil-control-0.4.0-1.fc44.noarch.rpm
sudo modprobe nct6775
anvil-control
```

Uygulama menüsünden **Anvil Control** de açılabilir. RPM, sonraki açılışlar için
`nct6775` modül yükleme ayarını kurar. GUI’yi root olarak çalıştırmayın; fan ayarı
yazılırken sistemin yönetici doğrulama penceresi açılır. RGB için isteğe bağlı
`sudo dnf install openrgb` paketini kurup Aydınlatma → Cihazları tara’yı kullanın.

Kaldırma: `sudo dnf remove anvil-control`. Kaldırma öncesinde fanları
**Önceki ayarlar** düğmesiyle geri yükleyin; paketi silmek donanımdaki eğriyi geri almaz.

## Özellikler

- Canlı sıcaklık bilgili anakart şeması ve ana sayfada fan merkezi.
- CPU/GPU kullanım ve sıcaklık, RAM için beş seçilebilir grafik.
- GPU fan etkinliği animasyonu, geçişler ve doluluk çubukları; hareketi kapatma seçeneği.
- Sensör araması, min/maks takibi, sıfırlama, duraklat/devam et.
- İsteğe bağlı sıcaklık uyarıları, olay günlüğü ve sistem tepsisi.
- Donanım/sürücü envanteri, JSON tanılama ve CSV ölçüm dışa aktarımı.
- Yerel çalışma: otomatik rapor gönderimi veya bulut hesabı gerekmez.

## Fan davranışı

Kanal numarası fiziksel CPU/kasa etiketini garanti etmez. Önce devir değişimini
gözleyerek fanı belirleyin. Bu sürüm yalnızca kanal 1–2, PWM modu ve PECI sıcaklık
kaynağıyla çalışır. Eğri 20–85 °C ve %50–100 aralığıyla sınırlıdır; son iki noktada
%100 gerekir. Sabit düşük hız veya fan durdurma sunulmaz.

Yazma sırasında tam hıza geçilir, değerler geri okunur. Hata durumunda önceki kayıt
geri yüklenir; geri yükleme de başarısız olursa tam hızda kalma hedeflenir.
İlk ayar yedeği root’a ait `/run/anvil-control` dizinindedir ve yeniden başlatmada
silinir. “Önceki ayarlar” o açılıştaki ilk Anvil değişikliği öncesine döner.
Eğri UEFI’ye kalıcı olarak kaydedilmez; uygulama kapandığında donanımda kalır.

## Doğrulama

Fedora 44 KDE / PRIME H610M-K D4 / i5-12400F / RTX 5060 Ti üzerinde:

- Kanal 1: yaklaşık 700 → **1.724 RPM**, kanal 2: yaklaşık 1.830 → **3.154 RPM** (tam hız).
- İki kanalda özel eğri yazma, geri okuma ve özgün ayarlara dönüş başarılı.
- Gerçek sistemde güç profili değişimi ve başlangıç profiline dönüş doğrulandı.
- 17 birim testi; hata durumunda geri alma, eğri doğrulama ve RGB mod ayrıştırması dahil.
- Gerçek telemetriyle yedi sayfa, arama, grafik, animasyon, JSON/CSV arayüz testi.

```bash
python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 tests/smoke_ui.py
```

Arayüz testi test makinesine özgüdür. Birim testleri gerçek fanlara yazmaz.
Kaynaktan GUI: `sudo dnf install python3-pyside6 pciutils`, ardından `python3 -m anvil`.
Fan yazma için root’a ait yardımcıyı sağlayan RPM kurulmalıdır.

## Sınırlar ve gizlilik

Deneysel **alpha**, imzasız RPM; ASUS veya Fedora tarafından onaylanmış değildir.
Şema temsili bileşen çizimidir, elektrik/pin bağlantısı referansı değildir.
NVIDIA birinci GPU telemetrisi desteklenir; AMD/Intel GPU ölçümleri henüz yoktur.
85 °C bildirim eşiği bir donanım güvenlik garantisi değildir. Uyarılar varsayılan
kapalıdır, 5 °C histerezis kullanır; duraklatıldığında uyarılar da durur.
Grafikler son 120, dışa aktarma son 3.600 ölçümü bellekte tutar; sıcaklık grafiği
0–100 °C aralığına kırpılır. Kesin okumalar sensör tablosundadır.

Seri numarası ve makine kimliği toplanmaz. Paylaşacağınız tanılama raporlarını
önceden inceleyin; anakart, BIOS, PCI ve sensör bilgileri içerir.

## English

Native Qt control center for ASUS desktops on Fedora KDE. Includes NCT6798 hardware
fan curves on PRIME H610M-K D4, monitoring, power profiles and optional OpenRGB
device controls. Experimental alpha; hardware support is explicitly scoped.

## Kaynaklar

- [Linux NCT6775/NCT6798 sürücüsü](https://www.kernel.org/doc/html/latest/hwmon/nct6775.html)
- [ASUS anakart özellikleri](https://www.asus.com/au/motherboards-components/motherboards/prime/prime-h610m-k-d4/techspec/)
- [NVIDIA NVML](https://docs.nvidia.com/deploy/nvml-api/) · [OpenRGB](https://openrgb.org/)
