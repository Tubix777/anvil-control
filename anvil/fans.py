from pathlib import Path
from .backend import read, number


# A profile is write-enabled only after its board, controller, channels and
# temperature-source behavior have been verified on physical hardware.
FAN_PROFILES = {
    'PRIME H610M-K D4': {'controller': 'nct6798', 'channels': (1, 2)},
}


def supports_fan_write(board):
    return board in FAN_PROFILES


def channels():
    found = []
    board = read('/sys/class/dmi/id/board_name')
    profile = FAN_PROFILES.get(board)
    if not profile:
        return found
    for hw in Path('/sys/class/hwmon').glob('hwmon*'):
        if read(hw/'name') != profile['controller']:
            continue
        for n in profile['channels']:
            if (hw/f'pwm{n}_enable').exists():
                found.append({'channel':n, 'rpm':number(hw/f'fan{n}_input'),
                              'mode':read(hw/f'pwm{n}_enable'), 'duty':number(hw/f'pwm{n}', 2.55),
                              'points':[[number(hw/f'pwm{n}_auto_point{i}_temp', 1000),
                                         number(hw/f'pwm{n}_auto_point{i}_pwm', 2.55)] for i in range(1, 6)]})
    return found
