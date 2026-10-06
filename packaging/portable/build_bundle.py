#!/usr/bin/env python3
"""Build an offline Linux x86_64 archive using hash-pinned upstream Qt wheels."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
QT_VERSION = '6.11.2'
WHEELS = {
    'PySide6-Essentials': ('pyside6_essentials-6.11.2-cp310-abi3-manylinux_2_34_x86_64.whl',
                         'aaf9f25f0f324874085fa5b26a610318db8a8e243cf85bb3e5400595191c7778'),
    'shiboken6': ('shiboken6-6.11.2-cp310-abi3-manylinux_2_34_x86_64.whl',
                 '7a7a0a72a9ed26c9bf77d42246b1c736486befb8f31aa2fb29957ea4cdd1c1c2'),
}
PYSIDE_SOURCE = ('pyside-setup-everywhere-src-6.11.2.tar.xz',
                 'cba47efbaad1bedd529725cbc14e21f156c7a19366f07b3edfbb076ffd7afdf8')


def upstream_licenses(cache):
    """Qt wheels omit license files; retain the matching upstream source notices."""
    filename, checksum = PYSIDE_SOURCE
    source = cache / filename
    if not source.exists():
        url = 'https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/' + filename
        print('Downloading matching Qt for Python source/license notices', flush=True)
        with urllib.request.urlopen(url, timeout=120) as response:
            contents = response.read()
        if hashlib.sha256(contents).hexdigest() != checksum:
            raise ValueError('Qt for Python source checksum mismatch')
        source.write_bytes(contents)
    if hashlib.sha256(source.read_bytes()).hexdigest() != checksum:
        raise ValueError('Cached Qt for Python source checksum mismatch')
    entries = {}
    with tarfile.open(source, 'r:xz') as archive:
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if member.isfile() and len(parts) == 3 and parts[1] == 'LICENSES' and parts[2].endswith('.txt'):
                entries['licenses/QtForPython/' + parts[2]] = (archive.extractfile(member).read(), 0o644)
    if not entries:
        raise ValueError('Matching Qt for Python source contains no expected license files')
    return entries


def source_version():
    match = re.search(r"^__version__\s*=\s*['\"]([0-9]+(?:\.[0-9]+)*)['\"]\s*$",
                      (ROOT / 'anvil' / '__init__.py').read_text(), re.MULTILINE)
    if not match:
        raise ValueError('Expected numeric dotted application version')
    return match.group(1)


def obtain_wheel(package, cache):
    filename, expected = WHEELS[package]
    target = cache / filename
    if not target.exists():
        metadata_url = 'https://pypi.org/pypi/' + package + '/' + QT_VERSION + '/json'
        with urllib.request.urlopen(metadata_url, timeout=60) as response:
            metadata = json.load(response)
        record = next(item for item in metadata['urls'] if item['filename'] == filename)
        if record['digests']['sha256'] != expected or not record['url'].startswith('https://files.pythonhosted.org/'):
            raise ValueError('Upstream wheel metadata does not match pinned release')
        print('Downloading ' + filename, flush=True)
        with urllib.request.urlopen(record['url'], timeout=120) as response:
            contents = response.read()
        if hashlib.sha256(contents).hexdigest() != expected:
            raise ValueError('Downloaded wheel checksum mismatch: ' + filename)
        target.write_bytes(contents)
    contents = target.read_bytes()
    if hashlib.sha256(contents).hexdigest() != expected:
        raise ValueError('Cached wheel checksum mismatch: ' + filename)
    return filename, contents


def bundle_entries(cache):
    version = source_version()
    entries = {}
    for name in ('install.py', 'run.py', 'anvil-control', 'README.md', 'THIRD_PARTY.md'):
        entries[name] = ((HERE / name).read_bytes(), 0o755 if name == 'anvil-control' else 0o644)
    entries['LICENSE'] = ((ROOT / 'LICENSE').read_bytes(), 0o644)
    entries['io.anvil.Control.svg'] = ((ROOT / 'packaging' / 'io.anvil.Control.svg').read_bytes(), 0o644)
    entries.update(upstream_licenses(cache))
    requirements = []
    for package, (_, checksum) in WHEELS.items():
        name, contents = obtain_wheel(package, cache)
        entries['wheels/' + name] = (contents, 0o644)
        requirements.append(package + '==' + QT_VERSION + ' --hash=sha256:' + checksum)
    entries['requirements.txt'] = (('\n'.join(requirements) + '\n').encode(), 0o644)
    for source in sorted((ROOT / 'anvil').glob('*.py')):
        if source.is_symlink() or not source.is_file():
            raise ValueError('Unexpected application source')
        entries['app/anvil/' + source.name] = (source.read_bytes(), 0o644)
    entries['bundle.json'] = ((json.dumps({'version': version, 'qt': QT_VERSION,
                              'architecture': 'x86_64', 'python': '>=3.10,<3.15',
                              'glibc': '>=2.34', 'monitor_only': True}, indent=2) + '\n').encode(), 0o644)
    sums = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                   for name, (data, _) in sorted(entries.items()))
    entries['SHA256SUMS'] = (sums.encode(), 0o644)
    return entries


def build(output, cache, epoch):
    entries = bundle_entries(cache)
    prefix = 'anvil-control-' + source_version() + '-linux-x86_64'
    with output.open('xb') as destination:
        with gzip.GzipFile(filename='', mode='wb', fileobj=destination, mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.GNU_FORMAT) as archive:
                for path, (contents, mode) in sorted(entries.items()):
                    info = tarfile.TarInfo(prefix + '/' + path)
                    info.mode, info.size, info.mtime = mode, len(contents), epoch
                    archive.addfile(info, io.BytesIO(contents))
    return output.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New .tar.gz output path; refuses to overwrite')
    parser.add_argument('--wheel-directory', type=Path, required=True, help='Download/cache pinned wheels here')
    args = parser.parse_args()
    output = args.output or Path.cwd() / ('anvil-control-' + source_version() + '-linux-x86_64.tar.gz')
    if not str(output).endswith('.tar.gz'):
        parser.error('Output path must end in .tar.gz')
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH', '0'))
    if epoch < 0:
        parser.error('SOURCE_DATE_EPOCH must be nonnegative')
    args.wheel_directory.mkdir(parents=True, exist_ok=True)
    print(build(output, args.wheel_directory, epoch))


if __name__ == '__main__':
    main()
