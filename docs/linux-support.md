# Linux dağıtımları — 0.14.0 alpha

Paket kurulumu ve pencere açılışı, fiziksel fan kontrolünden ayrı doğrulanır.
Konteynerler dağıtımın gerçek paketlerini kullanır; ana bilgisayara bu dağıtımlar
kurulmaz. Ekransız testin yanında Xvfb üzerinde gerçek Qt X11/xcb eklentisiyle
pencere açılışı da sınanır. Donanım sensörlerinin görünmesi yerel kernel ve
sürücülere bağlıdır.

| Sistem | Paket / Qt | Doğrulama |
| --- | --- | --- |
| Fedora 44 KDE, mevcut ASUS cihaz | RPM / sistem Qt | Salt okunur canlı arayüz testi; RPM dosya özeti doğrulaması |
| Fedora 44, temiz konteyner | Taşınabilir arşiv / Qt 6.11.2 | Çevrimdışı Qt, ekransız ve X11 pencere |
| Ubuntu 22.04 | Qt 6.11.2 içeren amd64 DEB | Temiz kurulum, kullanıcıya özel çevrimdışı Qt, ekransız ve X11 pencere |
| Ubuntu 24.04 | Qt 6.11.2 içeren amd64 DEB | Temiz kurulum, çevrimdışı Qt, ekransız ve X11 pencere |
| Debian 13 | Küçük DEB / sistem Qt 6.8.2.1 | Temiz kurulum, ekransız ve X11 pencere |
| Ubuntu 26.04 | Küçük DEB / sistem Qt 6.10.2 | Temiz kurulum, ekransız ve X11 pencere |
| Deepin 25, linuxdeepin konteyneri | Qt 6.11.2 içeren amd64 DEB | Kurulum, çevrimdışı Qt, ekransız ve X11 pencere; DDE masaüstü ayrıca sınanmadı |
| Arch Linux, 2026-10-06 paketleri | Taşınabilir arşiv / Qt 6.11.2 | Çevrimdışı Qt, X11 pencere; gerçek masaüstü/donanım ayrıca sınanmadı |
| Zorin 17 / 18 | Ubuntu ailesi için amd64 DEB hedefi | Ayrı Zorin ortamında henüz sınanmadı |

Zorin 17.3 Ubuntu 22.04, Zorin 18.1 Ubuntu 24.04 tabanlıdır ve DEB kullanır.
Bu, bir kurulum hedefi seçmemizi sağlar; başarılı Zorin testi sayılmaz.
[Zorin’in resmi sistem bilgisi](https://zorin.com/os/details/).

Arşiv, bundled DEB ve wheel kurulumu yalnız izleme içindir; ayrıcalıklı yardımcı,
polkit eylemi veya otomatik kernel modülü yapılandırması taşımaz. Modül ve konsol
başlatıcıları izleme modunu açıkça etkinleştirir. Fedora RPM mevcut kontrol
başlatıcısını korur. Yeni dağıtımlarda doğrulanmamış fan yazımını açmayın.

## Paket gereksinimleri

- **Bundled amd64 DEB:** Python 3.10–3.14, glibc ≥ 2.34, venv ve apt tarafından
  kurulan GUI kütüphaneleri. Qt dosyaları pakettedir; ilk açılış çevrimdışıdır.
- **Küçük all DEB:** Python ≥ 3.10 ve dağıtımın `python3-pyside6.qtwidgets`
  paketi. Ubuntu 22.04/24.04 standart depolarında bu paket yoktur; bundled çeşidi
  kullanın. Mimari bağımsız paket, her mimarinin test edildiği anlamına gelmez.
- **Taşınabilir arşiv:** Linux x86_64, Python 3.10–3.14, glibc ≥ 2.34,
  venv/ensurepip ve yerel GUI kütüphaneleri. ARM ve Alpine/musl bu arşivde yoktur.
- **Wheel:** aynı Python aralığı ve PySide6-Essentials 6.11.2 bağımlılığı.
  Sistem Python’u yerine venv içinde kurun. Wheel, PyPI’da yayımlanmış sayılmaz;
  GitHub sürümündeki dosya geliştirme kurulumları içindir.

DEB çeşitlerini aynı anda kurmayın. `sudo apt install ./paket.deb` bağımlılıkları
çözer; `dpkg -i` tek başına bunu yapmaz. Uygulamayı normal masaüstü kullanıcısı
olarak açın. [Taşınabilir paket yönergeleri](../packaging/portable/README.md),
[DEB derleme yönergeleri](../packaging/debian/README.md).

## Tekrarlanabilir doğrulama

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 tests/smoke_ui.py
python3 packaging/portable/test_container.py --image docker.io/library/ubuntu:24.04 --artifact /tam/yol/anvil-control_0.14.0~alpha1-1_amd64.deb
```

Bu sürümün 98 birim testi geçti. Son komut yalnız oluşturduğu, adı tekil olan geçici Podman konteynerini değiştirir
ve sonunda kaldırır. Kurulu paket koduyla ölçüm, beş sayfa, tema, sensör filtresi
ve yazma korumaları test edilir. Qt geri çağrı hataları testi başarısız kılar.
GitHub Actions matrisi sonraki değişikliklerde aynı paket ve pencere testlerini
Ubuntu, Debian, Deepin, Fedora ve Arch hedeflerinde çalıştırır. CI eklenmesi,
başarılı koşu sonucu olmadan yeni bir dağıtımın doğrulandığı anlamına gelmez.

## Sıradaki dağıtım işleri

Zorin’in gerçek masaüstü ortamı, Wayland oturumu ve paket güncelleme/kaldırma
döngüsü ayrı hedeflerdir. ARM64 paketi için uygun Qt dosyaları ve gerçek mimari
testi gerekir. Flatpak/AppImage bu sürümde yayımlanmıyor; arşive bu adlar verilmez.
