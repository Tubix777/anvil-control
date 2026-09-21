from pathlib import Path
from .backend import read, number


def channels():
    found = []
    if read('/sys/class/dmi/id/board_name') != 'PRIME H610M-K D4':
        return found
    for hw in Path('/sys/class/hwmon').glob('hwmon*'):
        if read(hw/'name') != 'nct6798':
            continue
        for n in (1, 2):
            if (hw/f'pwm{n}_enable').exists():
                found.append({'channel':n, 'rpm':number(hw/f'fan{n}_input'),
                              'mode':read(hw/f'pwm{n}_enable'), 'duty':number(hw/f'pwm{n}', 2.55),
                              'points':[[number(hw/f'pwm{n}_auto_point{i}_temp', 1000),
                                         number(hw/f'pwm{n}_auto_point{i}_pwm', 2.55)] for i in range(1, 6)]})
    return found
