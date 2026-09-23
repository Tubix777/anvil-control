import json
from pathlib import Path
from .backend import read, number, is_asus_vendor


# A profile is write-enabled only after its board, controller, channels and
# temperature-source behavior have been verified on physical hardware.
FAN_PROFILES = {
    'PRIME H610M-K D4': {'controller': 'nct6798', 'channels': (1, 2)},
}

# Temperature-controlled presets, not fixed RPM targets. The privileged helper
# independently validates every point before writing to the verified board.
FAN_PRESETS = {
    'calm': ('Sakin', ((30, 50), (45, 55), (60, 70), (75, 100), (85, 100))),
    'balanced': ('Dengeli', ((30, 60), (45, 70), (60, 85), (75, 100), (85, 100))),
    'cool': ('Yüksek soğutma', ((30, 70), (45, 80), (60, 95), (75, 100), (85, 100))),
}


def preset_points(key):
    preset = FAN_PRESETS.get(key)
    return [list(point) for point in preset[1]] if preset else None


def supports_fan_write(board, vendor):
    """A matching model name alone must never enable a write control."""
    return is_asus_vendor(vendor) and board in FAN_PROFILES


def fan_result(ok, output, error, action, channel):
    """Report success only for a matching, read-back-verified helper response."""
    if not ok:
        return False, 'Fan işlemi başarısız: ' + (error.strip() or 'Yetkilendirme iptal edildi veya yardımcı başlatılamadı.')
    try:
        result = json.loads(output)
    except (TypeError, ValueError):
        return False, 'Fan yardımcısından geçerli doğrulama yanıtı alınamadı.'
    if (not isinstance(result, dict) or result.get('ok') is not True
            or result.get('action') != action or result.get('channel') != channel
            or not isinstance(result.get('verified'), dict) or not result['verified']):
        return False, 'Fan yardımcısının geri okuma yanıtı uyuşmuyor.'
    verified = result['verified']
    stem = f'pwm{channel}'
    expected = {stem + '_enable'} | {f'{stem}_auto_point{i}_{suffix}'
                                     for i in range(1, 6) for suffix in ('temp', 'pwm')}
    if (set(verified) != expected or any(type(value) is not int for value in verified.values())
            or (action == 'curve' and verified[stem + '_enable'] != 5)
            or (action == 'full' and verified[stem + '_enable'] != 0)):
        return False, 'Fan ayarının geri okuması eksik veya beklenen modda değil.'
    return True, 'Fan ayarı uygulandı ve donanımdan geri okunarak doğrulandı.'


def channels(root=Path('/sys/class/hwmon'), board=None, vendor=None):
    found = []
    board = board if board is not None else read('/sys/class/dmi/id/board_name')
    vendor = vendor if vendor is not None else read('/sys/class/dmi/id/board_vendor')
    if not supports_fan_write(board, vendor):
        return found
    profile = FAN_PROFILES.get(board)
    for hw in root.glob('hwmon*'):
        if read(hw/'name') != profile['controller']:
            continue
        for n in profile['channels']:
            stem = f'pwm{n}'
            required = [f'{stem}_{suffix}' for suffix in ('enable', 'mode', 'temp_sel')]
            required += [f'{stem}_auto_point{i}_{suffix}' for i in range(1, 6)
                         for suffix in ('temp', 'pwm')]
            source = read(hw/f'{stem}_temp_sel')
            if (all((hw/name).exists() for name in required) and source.isdecimal()
                    and 'PECI' in read(hw/f'temp{source}_label')
                    and number(hw/f'temp{source}_input') is not None
                    and read(hw/f'{stem}_mode') == '1'
                    and read(hw/f'{stem}_enable') in ('0', '5')):
                found.append({'channel':n, 'rpm':number(hw/f'fan{n}_input'),
                              'mode':read(hw/f'pwm{n}_enable'), 'duty':number(hw/f'pwm{n}', 2.55),
                              'points':[[number(hw/f'pwm{n}_auto_point{i}_temp', 1000),
                                         number(hw/f'pwm{n}_auto_point{i}_pwm', 2.55)] for i in range(1, 6)]})
    return found
