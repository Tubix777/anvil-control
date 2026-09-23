"""Read-only hardware discovery and an explicitly invoked power-profile adapter."""
import ctypes as C
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path


def read(path, default=""):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return default


def run(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def number(path, divisor=1):
    try:
        return float(read(path)) / divisor
    except (ValueError, ZeroDivisionError):
        return None


def cpu_temperature(readings):
    """Return the hottest reading from known CPU temperature drivers only."""
    cpu_chips = {'coretemp', 'k10temp', 'zenpower'}
    values = [s['value'] for s in readings
              if s['unit'] == '°C' and s['chip'].casefold() in cpu_chips]
    return max(values) if values else None


def is_asus_vendor(vendor):
    """Recognize DMI ASUS and ASUSTeK spellings without guessing from model text."""
    return 'asus' in (vendor or '').casefold()


def sensors(root=Path('/sys/class/hwmon')):
    result = []
    for hw in sorted(root.glob('hwmon*')):
        chip = read(hw / 'name', hw.name)
        for kind, unit, scale in [('temp', '°C', 1000), ('fan', 'RPM', 1), ('power', 'W', 1000000)]:
            for file in sorted(hw.glob(kind + '*_input')):
                value = number(file, scale)
                if value is not None:
                    stem = file.name.removesuffix('_input')
                    result.append(dict(chip=chip, label=read(hw / (stem + '_label'), stem),
                                       value=value, unit=unit, path=str(file)))
    return result


DBUS = ['net.hadess.PowerProfiles', '/net/hadess/PowerProfiles', 'net.hadess.PowerProfiles']


def property_value(name):
    try:
        return json.loads(run(['busctl', '--json=short', 'get-property', *DBUS, name]))['data']
    except (ValueError, KeyError, TypeError):
        return None


def set_profile(profile):
    available = property_value('Profiles') or []
    allowed = [p.get('Profile', {}).get('data') for p in available]
    if profile not in allowed:
        return False, 'Bu profil sistem tarafından sunulmuyor.'
    try:
        p = subprocess.run(['busctl', 'set-property', *DBUS, 'ActiveProfile', 's', profile],
                           capture_output=True, text=True, timeout=20)
        if p.returncode:
            return False, p.stderr.strip() or 'Profil değiştirilemedi.'
        actual = property_value('ActiveProfile')
        return actual == profile, ('Profil uygulandı.' if actual == profile else 'Profil değişikliği doğrulanamadı.')
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


class Nvidia:
    """Optional NVML telemetry; no GPU setting writes."""
    def __init__(self):
        self.lib = None
        try:
            lib = C.CDLL('libnvidia-ml.so.1')
            if lib.nvmlInit_v2() != 0:
                return
            self.lib = lib
        except (OSError, AttributeError):
            pass

    def sample(self):
        if not self.lib:
            return None
        try:
            dev = C.c_void_p()
            if self.lib.nvmlDeviceGetHandleByIndex_v2(C.c_uint(0), C.byref(dev)):
                return None
            name = C.create_string_buffer(128)
            self.lib.nvmlDeviceGetName(dev, name, C.c_uint(128))
            out = {'name': name.value.decode(errors='replace')}
            for key, fun, scale in [('temperature', 'nvmlDeviceGetTemperature', 1),
                                    ('power', 'nvmlDeviceGetPowerUsage', 1000),
                                    ('fan', 'nvmlDeviceGetFanSpeed', 1)]:
                v = C.c_uint()
                args = [dev, C.c_uint(0), C.byref(v)] if key == 'temperature' else [dev, C.byref(v)]
                if getattr(self.lib, fun)(*args) == 0:
                    out[key] = v.value / scale
            class Util(C.Structure):
                _fields_ = [('gpu', C.c_uint), ('memory', C.c_uint)]
            class Memory(C.Structure):
                _fields_ = [('total', C.c_ulonglong), ('free', C.c_ulonglong), ('used', C.c_ulonglong)]
            util, mem = Util(), Memory()
            if self.lib.nvmlDeviceGetUtilizationRates(dev, C.byref(util)) == 0:
                out['usage'] = util.gpu
            if self.lib.nvmlDeviceGetMemoryInfo(dev, C.byref(mem)) == 0:
                out.update(memory_used=mem.used, memory_total=mem.total)
            return out
        except (AttributeError, OSError):
            return None


class AmdGpu:
    """Read-only amdgpu sysfs telemetry; absent fields remain unknown."""
    def __init__(self, root=Path('/sys/class/drm')):
        self.root = root

    def sample(self):
        for card in sorted(self.root.glob('card[0-9]*')):
            device = card / 'device'
            if not (device / 'driver').exists() or (device / 'driver').resolve().name != 'amdgpu':
                continue
            hw = next((p for p in sorted((device / 'hwmon').glob('hwmon*'))
                       if read(p / 'name') == 'amdgpu'), None)
            out = {'name': 'AMD Radeon (amdgpu)', 'source': 'amdgpu/sysfs'}
            usage = number(device / 'gpu_busy_percent')
            if usage is not None and 0 <= usage <= 100:
                out['usage'] = usage
            total = number(device / 'mem_info_vram_total')
            used = number(device / 'mem_info_vram_used')
            if total is not None and total > 0 and used is not None and 0 <= used <= total:
                out.update(memory_total=total, memory_used=used)
            if hw:
                temperature = number(hw / 'temp1_input', 1000)
                power = number(hw / 'power1_average', 1000000)
                if power is None:
                    power = number(hw / 'power1_input', 1000000)
                fan_rpm = number(hw / 'fan1_input')
                if temperature is not None and -20 <= temperature <= 150:
                    out['temperature'] = temperature
                if power is not None and power >= 0:
                    out['power'] = power
                if fan_rpm is not None and fan_rpm >= 0:
                    out['fan_rpm'] = fan_rpm
            if len(out) > 2:
                return out
        return None


class Monitor:
    def __init__(self):
        self.previous = None
        self.gpu = Nvidia()
        self.amd_gpu = AmdGpu()
        self.identity = self.discover()

    def discover(self):
        osdata = dict(line.split('=', 1) for line in read('/etc/os-release').splitlines() if '=' in line)
        cpu = next((x.split(':', 1)[1].strip() for x in read('/proc/cpuinfo').splitlines()
                    if x.startswith('model name')), 'Bilinmiyor')
        vendor = read('/sys/class/dmi/id/board_vendor')
        board = read('/sys/class/dmi/id/board_name', 'Bilinmiyor')
        return dict(board=board,
                    vendor=vendor, asus=is_asus_vendor(vendor),
                    bios=read('/sys/class/dmi/id/bios_version'),
                    bios_date=read('/sys/class/dmi/id/bios_date'),
                    os=osdata.get('PRETTY_NAME', platform.system()).strip('"'),
                    kernel=platform.release(), cpu=cpu,
                    pci=run(['lspci', '-k']),
                    pwm=[str(p) for p in Path('/sys/class/hwmon').glob('hwmon*/pwm[0-9]')],
                    openrgb=shutil.which('openrgb'))

    def sample(self):
        try:
            vals = [int(x) for x in read('/proc/stat').splitlines()[0].split()[1:9]]
            if len(vals) < 5:
                raise ValueError('Eksik CPU sayacı')
            total, idle = sum(vals), vals[3] + vals[4]
        except (IndexError, ValueError):
            total = idle = None
        usage = None
        if self.previous and total is not None:
            dt, di = total - self.previous[0], idle - self.previous[1]
            usage = max(0, min(100, 100 * (dt-di) / dt)) if dt > 0 else None
        self.previous = (total, idle) if total is not None else None
        mem = {}
        for line in read('/proc/meminfo').splitlines():
            try:
                key, value = line.split(':', 1)
                mem[key] = int(value.strip().split()[0]) * 1024
            except (ValueError, IndexError):
                continue
        memory_total = mem.get('MemTotal')
        memory_available = mem.get('MemAvailable')
        memory_used = (max(0, memory_total-memory_available)
                       if memory_total is not None and memory_available is not None else None)
        ss = sensors()
        cpu_temp = cpu_temperature(ss)
        disk = shutil.disk_usage('/')
        uptime = read('/proc/uptime').split()
        return dict(time=time.time(), cpu_usage=usage, cpu_temp=cpu_temp,
                    cpu_mhz=number('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 1000),
                    memory_used=memory_used, memory_total=memory_total,
                    disk_used=disk.used, disk_total=disk.total,
                    uptime=uptime[0] if uptime else '', sensors=ss,
                    gpu=self.gpu.sample() or self.amd_gpu.sample(),
                    profile=property_value('ActiveProfile'), profiles=property_value('Profiles') or [])
