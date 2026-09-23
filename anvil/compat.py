"""Explain capabilities detected on this system without implying universal writes."""

from .backend import is_asus_vendor
from .fans import supports_fan_write


def capability_report(identity, sample, write_channels, helper_installed=True):
    """Return display-ready capability rows for any ASUS board (or other PC)."""
    readings = sample.get('sensors') or []
    temperatures = sum(item.get('unit') == '°C' for item in readings)
    fan_rpm = sum(item.get('unit') == 'RPM' for item in readings)
    pwm = len(identity.get('pwm') or [])
    profiles = sample.get('profiles') or []
    gpu = sample.get('gpu') or {}
    asus = is_asus_vendor(identity.get('vendor'))
    verified = supports_fan_write(identity.get('board'), identity.get('vendor'))
    if verified and write_channels and helper_installed:
        fan_write = f'Doğrulanmış kanal: {", ".join(map(str, write_channels))}'
        write_summary = 'hazır'
    elif verified and write_channels:
        fan_write = 'Donanım kanalı algılandı; güncel RPM yardımcısı gerekli'
        write_summary = 'RPM gerekli'
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
        ('Anakart', ('ASUS · ' if asus else 'Genel PC · ') + (identity.get('board') or 'Bilinmiyor')),
        ('Sıcaklık sensörleri', f'{temperatures} okuma' if temperatures else 'Sürücü verisi yok'),
        ('Fan devirleri', f'{fan_rpm} okuma' if fan_rpm else 'Sürücü verisi yok'),
        ('PWM arayüzleri', f'{pwm} görüldü; görünmesi yazma izni vermez' if pwm else 'Görünmüyor'),
        ('GPU telemetrisi', gpu.get('name') or 'Kullanılamıyor'),
        ('Güç profilleri', f'{len(profiles)} sunuluyor' if profiles else 'Servis verisi yok'),
        ('Anakart fan yazımı', fan_write),
    ]
    overview = ('ASUS anakart algılandı' if asus else 'ASUS dışı · genel izleme')
    overview += f'  ·  {temperatures} sıcaklık / {fan_rpm} fan okuması  ·  Fan yazma: '
    overview += write_summary
    return overview, rows
