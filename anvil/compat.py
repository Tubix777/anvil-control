"""Explain capabilities detected on this system without implying universal writes."""

from .backend import is_asus_vendor, profile_names
from .fans import supports_fan_write


def capability_report(identity, sample, write_channels, helper_installed=True, monitor_only=False):
    """Return display-ready capability rows for any ASUS board (or other PC)."""
    readings = sample.get('sensors') or []
    temperatures = sum(item.get('unit') == '°C' for item in readings)
    fan_rpm = sum(item.get('unit') == 'RPM' for item in readings)
    pwm = len(identity.get('pwm') or [])
    profiles = profile_names(sample.get('profiles'))
    gpu = sample.get('gpu') or {}
    asus = is_asus_vendor(identity.get('vendor'))
    verified = supports_fan_write(identity.get('board'), identity.get('vendor'))
    if monitor_only:
        fan_write = 'Bu kurulum yalnız izleme için; yazma kapalı'
        write_summary = 'kapalı'
    elif verified and write_channels and helper_installed:
        fan_write = f'Doğrulanmış kanal: {", ".join(map(str, write_channels))}'
        write_summary = 'hazır'
    elif verified and write_channels:
        fan_write = 'Donanım kanalı algılandı; paketli fan yardımcısı gerekli'
        write_summary = 'yardımcı gerekli'
    elif verified:
        fan_write = 'Doğrulanmış kart; uygun güvenli kanal algılanmadı'
        write_summary = 'kapalı'
    elif asus:
        fan_write = 'Bu modelde yazma henüz doğrulanmadı (salt okunur)'
        write_summary = 'kapalı'
    else:
        fan_write = 'ASUS dışı sistemde kapalı'
        write_summary = 'kapalı'
    rows = [
        ('İşletim sistemi', identity.get('os') or 'Linux'),
        ('Kurulum kapsamı', 'Yalnız izleme' if monitor_only else 'Algılanan kontrol desteği'),
        ('Anakart', ('ASUS · ' if asus else 'Genel PC · ') + (identity.get('board') or 'Bilinmiyor')),
        ('Sıcaklık sensörleri', f'{temperatures} okuma' if temperatures else 'Sürücü verisi yok'),
        ('Fan devirleri', f'{fan_rpm} okuma' if fan_rpm else 'Sürücü verisi yok'),
        ('PWM arayüzleri', f'{pwm} görüldü; görünmesi yazma izni vermez' if pwm else 'Görünmüyor'),
        ('GPU telemetrisi', gpu.get('name') or 'Kullanılamıyor'),
        ('Güç profilleri',
         (f'{len(profiles)} sunuluyor; değiştirme kapalı' if monitor_only else f'{len(profiles)} sunuluyor')
         if profiles else 'Servis verisi yok'),
        ('Anakart fan yazımı', fan_write),
    ]
    tools = identity.get('tools')
    if tools is not None:
        missing = [label for key, label in [('lspci', 'PCI listesi (pciutils)'),
                   ('busctl', 'güç profili sorgusu (busctl)'), ('openrgb', 'RGB (OpenRGB)')]
                   if not tools.get(key)]
        rows.append(('İsteğe bağlı araçlar', ', '.join(missing) + ' eksik' if missing else 'Bulundu'))
    overview = ('ASUS anakart algılandı' if asus else 'ASUS dışı · genel izleme')
    overview += f'  ·  {temperatures} sıcaklık / {fan_rpm} fan okuması  ·  Fan yazma: '
    overview += write_summary
    return overview, rows
