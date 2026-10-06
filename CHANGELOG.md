# Değişiklikler

## 0.14.0 — 2026-10-06

- Fedora dışına yönelik iki DEB çeşidi, Qt bağımlılıklarını yanında taşıyan çevrimdışı Linux x86_64 arşivi ve standart Python wheel paketi eklendi. İlk açılış Qt’yi özel kullanıcı ortamında hazırlar; sistem Python’unu değiştirmez.
- Ubuntu 22.04/24.04, Debian 13, Ubuntu 26.04, Deepin 25 ve Arch için kurulum/pencere açılışı testleri yapıldı; gerçek donanım desteği ayrı tutuldu. Zorin ayrı ortamda henüz sınanmadı.
- Yeni dağıtım paketlerinde fan, güç profili ve RGB yazımı kapalıdır. Konsol ve `python -m anvil` başlatmaları da izleme modunu etkinleştirir. Fedora’nın mevcut kontrol başlatıcısı korunur.
- Ana ekran sadeleşti: teknik fan eğrisi ve devir geçmişi klavyeyle açılan ayrıntı panelinde; canlı devirler ve kontroller görünür kaldı. Sistem dağıtımı ve eksik isteğe bağlı araçlar gösterilir.
- Zaten etkin olan aynı fan ayarını tekrar uygulamak artık gereksiz tam hız geçişi yapmaz. Bütün alanlar yeniden doğrulanır. Gerçek değişikliklerin son geri okuma ve geri alma kontrolleri güçlendirildi.
- Tekrarlanan sıfır RPM okumaları, belirgin dalgalanma ve ani değişimler gözlem mesajı üretir. Tolerans ve tepki süreleri okunur; bu, BIOS kaynaklı dalgalanmanın tamamen giderildiği iddiası değildir.
- Bozuk profil verisi, hatalı kodlanmış `os-release` ve profil komutunun metin çözümleme hatası için çökme/askıda kalma düzeltmeleri eklendi.
- Dağıtım paketleri için ekransız ve sanal X11 test düzeneği ile GitHub Actions matrisi eklendi. Qt dosyaları ve kaynak/lisans bildirimi hash ile doğrulanır.

## 0.13.12 — 2026-10-01

- Sensör ve donanım tabloları mevcut hücreleri yeniden kullanır; yalnız değişen metinler güncellenir. Sabit bilgiler her ölçümde yeniden oluşturulmaz.
- Canlı değer güncellemesi, seçili satırın korunması ve filtreleme sırasında eski değerlerin temizlenmesi test edildi.
- Yerel, ekransız 64 × 5 hücre ölçümünde (1.000 yenileme, beş koşunun ortancası) tablo güncelleme süresi değişmeyen veride %66, satır başına bir değer değiştiğinde %51 azaldı. Bu, uygulamanın toplam CPU kullanımı ölçümü değildir.

## 0.13.11 — 2026-09-24

- Fan eğrisi işleminin başarı mesajı artık dönen her sıcaklık ve PWM noktasını gönderilen eğriyle birebir karşılaştırıyor. Mod doğru olsa bile noktalardan biri farklıysa doğrulanmış başarı iddia edilmiyor.
- Asenkron sonuçta karşılaştırılan eğri, işlem başında gerçekten gönderilen JSON’un kopyasıdır; sonradan değişebilen arayüz verisi sonucu etkilemez.
- Ayrıcalıklı yardımcı, donanım yazma davranışı, güç profili ve yetki modeli değişmedi.

## 0.13.10 — 2026-09-24

- Fan işlemi sürerken veya tamamlanıp yeni okuma beklenirken mevcut eğri noktaları gösterilmiyor; işlem ortasındaki karma eski/yeni noktalar etkin donanım eğrisi gibi sunulmuyor.
- İşlemle çakışmayan yeni başarılı ölçümden sonra seçili kanalın eğrisi yeniden gösteriliyor. Bu arada fan ayarı düğmeleri kapalı kalıyor.
- Fan donanımına yazma, güç profili ve ayrıcalıklı yardımcının yetkileri değişmedi.

## 0.13.9 — 2026-09-24

- Genel hwmon sensörlerinde negatif fan RPM okumaları artık geçerli devir sayılmıyor; sensör tablosu ve fan sayacı bu geçersiz değeri göstermiyor.
- 0 RPM geçerli okuma olarak korunuyor. Negatif sıcaklık okumaları fan filtresinden etkilenmiyor.
- Fan donanımına yazma, güç profili ve ayrıcalıklı yardımcının yetkileri değişmedi.

## 0.13.8 — 2026-09-24

- İlk başarılı ölçümden önce, izleme duraklatıldığında ve ölçüm hatasında fan ayarı yazan düğmeler kapalı kalıyor; yeni başarılı okuma sonrasında yeniden açılıyor.
- Önceden açılmış eğri düzenleyicisinden duraklatma veya hata sonrası gelen yazma isteği de iptal ediliyor. Son okunan kanal ve eğri salt okunur olarak incelenebiliyor.
- Fan donanımına yazma, güç profili ve ayrıcalıklı yardımcının yetkileri değişmedi.

## 0.13.7 — 2026-09-24

- Ana sayfa fan paneli artık 0 RPM okuyan sensörlerden yola çıkıp tüm fiziksel fanların durduğunu iddia etmiyor. Pozitif devir okuması sayısını ve pozitif okuma yoksa bunu gösteriyor.
- Salt okunur sensör açıklaması dışında fan donanımı, güç profili ve yetki modeli değişmedi.

## 0.13.6 — 2026-09-24

- İzleme durakladığında, yeni ölçüm beklenirken veya ölçüm hata verdiğinde genel fan RPM listesi de açıkça **son okuma** olarak işaretleniyor. Yalnızca başarılı yeni ölçüm bu işareti kaldırıyor; eski devir canlı veri gibi görünmüyor.
- Fan yazımı, güç profili ve yetki modeli değişmedi.

## 0.13.5 — 2026-09-24

- Doğrulanmamış ASUS anakartlarında fan paneli artık mevcut donanım eğrisinin incelenebileceğini ima etmiyor. Varsa fan devir sensörlerinin izlenebildiğini, hazır eğrilerin yalnız önizleme olduğunu ve fan yazımının kapalı kaldığını açıkça belirtiyor.
- Desteklenmeyen kart için arayüz testi eklendi. Fan donanımına yazma, güç profili ve yetki modeli değişmedi.

## 0.13.4 — 2026-09-24

- Ekran okuyucuya sunulan fan eğrisi ve son devir değişimi metinleri artık seçili kanal ile ölçüm değiştikçe yenileniyor. Sabit erişilebilir adların canlı metni gizlemesi giderildi; açıklayıcı bağlam erişilebilir açıklama olarak korunuyor.
- Kanal değişimi ve ölçüm hatasındaki erişilebilir metinler test edildi. Fan donanımına yazma, güç profili ve yetki modeli değişmedi.

## 0.13.3 — 2026-09-24

- NCT6798’in sunduğu isteğe bağlı ikincil sıcaklık kaynağı seçimi, sensör etiketi ve geçerli sıcaklığı seçili kanalın donanım eğrisi yanında salt okunur gösteriliyor. Alan yoksa kapalı varsayılmıyor; devre dışı/atanmamış seçim ve okunamayan veri ayrı belirtiliyor.
- İkincil alanın eksik veya bozuk olması sağlam fan kanalını gizlemiyor. Tam hız modunda seçili kaynak otomatik kontrol uygulanıyormuş gibi sunulmuyor; fan hızlanmasının nedeni olduğu iddia edilmiyor.
- Fan donanımına yazma, güç profili ve yetki modeli değişmedi.

## 0.13.2 — 2026-09-24

- NCT6798 Smart Fan IV donanım eğrisindeki beşinci nokta artık normal eğri adımı yerine ayrı **kritik eşik** olarak gösteriliyor. Eşikteki PWM geri okuması aynen belirtiliyor; %100’den düşükse tam hız varsayılmıyor.
- Sysfs’ten gelen `NaN` ve sonsuz sensör okumaları artık geçerli sıcaklık veya RPM gibi gösterilmiyor.
- Bu sürüm fan donanımına yazmıyor; güç profili ve yetki modeli değişmedi.

## 0.13.1 — 2026-09-24

- İzleme duraklatıldığında veya ölçüm başarısız olduğunda fan kanalındaki RPM ve donanım eğrisi son okuma olarak işaretleniyor; eski geçmiş artık canlı “son 60 sn” gibi sunulmuyor.
- İzleme yeniden başladığında veya hata sonrası ilk başarılı ölçümde RPM karşılaştırması sıfırdan başlıyor. Kanal değişimi sırasında uyarı korunuyor; yeni ölçümle normal gösterim geri geliyor.
- Fan donanımına yazma, güç profili ve yetki modeli değişmedi.

## 0.13.0 — 2026-09-24

- Ana sayfada seçili doğrulanmış fan kanalının son 60 saniyedeki geçerli RPM ölçüm sayısı, aralığı ve iki son ölçüm arasındaki değişim gösteriliyor. Kanal geçmişleri karışmıyor; görünmeyen kanalın geçmişi temizleniyor.
- Geçmiş yalnız uygulama açıkken bellekte tutuluyor ve raporlara eklenmiyor. Bu gösterge ani hızlanmayı gözlemlemek içindir; nedenini tek başına teşhis etmez.
- Fan donanımına yazma, güç profili ve ayrıcalıklı yardımcının yetkileri değişmedi.

## 0.12.4 — 2026-09-24

- Fan arayüzü, ayrıcalıklı yardımcıyla aynı denetleyici kuralını uyguluyor: sistemde birden fazla NCT6798 kimliği görünürse belirsiz kanalları yazılabilir olarak sunmuyor.
- Bu durum ile farklı adlı ikinci bir sensörün normal çalışmayı engellememesi test edildi. Fan yardımcısı ve donanım ayarları değiştirilmedi.
- Arayüz smoke testinin fan animasyonu denetimi, aynı anda gelen sensör yenilemesinden etkilenmeyecek şekilde kararlılaştırıldı.

## 0.12.3 — 2026-09-24

- Fan işlemi sürerken kanal seçimi değişse bile bekleme ve sonuç mesajları işlemin başlatıldığı kanal numarasını gösteriyor.
- Özel eğri penceresi açıkken seçili kanal değişirse yanlış kanala yazma önleniyor; işlem iptal edilip eğrinin yeniden açılması isteniyor. Kabul anında kanal bir kez daha denetleniyor.
- Bu iki durum için donanım komutu çalıştırmayan arayüz testleri eklendi. Fan yazma yardımcısı, güç profili ve donanım ayarları değiştirilmedi.

## 0.12.2 — 2026-09-24

- Doğrulanmış kartta PECI sıcaklığı veya beş donanım eğrisi noktası bozuk, eksik ya da aralık dışındaysa ilgili kanal artık yazılabilir olarak sunulmuyor. Sağlam diğer kanal görünmeye devam eder.
- BIOS’un hazır eğrisinin son kritik sıcaklık noktası, kullanıcı tarafından yazılacak yeni eğrinin kısıtlarıyla karıştırılmıyor; gerçek donanımda görülen sırası farklı ve 125 °C kritik noktalar okunabilir kalıyor.
- Bozuk `NaN`/sonsuz/sayı olmayan sysfs verileri ve iki kanalın birbirinden bağımsız değerlendirilmesi için testler eklendi. Ayrıcalıklı fan yardımcısı ve donanım ayarları değiştirilmedi.

## 0.12.1 — 2026-09-24

- Fan kanalını seçip donanım eğrisini incelemek artık yazma yardımcısının kurulu olmasına veya başka bir donanım işleminin bitmesine bağlı değil. Yazma düğmeleri bu durumlarda kapalı kalır; fan donanımı değiştirilmez.
- Bu ayrımı doğrulayan arayüz testleri genişletildi ve fan kanalı seçicisine erişilebilir ad eklendi.

## 0.12.0 — 2026-09-24

- Doğrulanmış fan kanalları anlık RPM ile etiketleniyor; yalnızca bir fan dönüyorsa ilk seçim ona yöneliyor, kullanıcının kanal seçimi korunuyor. Kanal numarası fiziksel CPU/kasa bağlantısını kanıtlamaz.
- Seçili kanalın donanımdan geri okunan etkin beş noktalı eğrisi, PECI sıcaklık kaynağı ve sürücü sunuyorsa hızlanma/yavaşlama süreleri hazır eğri önizlemesinden ayrı gösteriliyor. Tam hız modunda kayıtlı eğri etkinmiş gibi sunulmuyor.
- Fan yazma davranışı, güç profili ve sistem fan ayarları değiştirilmedi; ani devir artışının nedenini incelemek için salt okunur bilgiler ve regresyon testleri eklendi.

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
