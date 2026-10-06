# Katkıda bulunma

Hata raporuna uygulama sürümü, dağıtım/kernel, anakart modeli ve yeniden üretme
adımlarını ekleyin. Parola, token, seri numarası veya özel günlükleri paylaşmayın.

Yeni anakart fan desteği için denetleyici modeli, kanal eşlemesi, sıcaklık kaynağı,
geri okuma ve geri yükleme kanıtı gerekir. Donanım kısıtlamalarını yalnızca arayüzde
kaldırmak yeterli değildir; ayrıcalıklı yardımcıda doğrulama da gereklidir.

Değişiklikler için birim testlerini çalıştırın. GUI değişikliklerinde
`tests/smoke_ui.py` testini uygun donanım üzerinde kullanın ve görünümü inceleyin.
Fan testleri normal birim testlerde geçici dosyalarla yapılır, gerçek donanıma yazmaz.

Linux paketleri için `docs/linux-support.md` test matrisini güncelleyin.
`packaging/portable/test_container.py` kurulu paketi geçici Podman ortamında
ekransız ve X11 ile açar. Test edilmeyen türev dağıtımı desteklenmiş saymayın.
Konteyner testleri fiziksel sensör/fan doğrulamasının yerine geçmez. GitHub Actions
matrisi sürüm paketlerini gerçek kaynaklardan yeniden üretip sınar.

Kod MIT lisansı altındadır. Görseller ve üçüncü taraf içerikler için lisansını belirtin.
