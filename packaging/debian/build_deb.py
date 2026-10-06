#!/usr/bin/env python3
"""Build a deterministic monitoring-only Debian package without root or dpkg."""
import argparse
import gzip
import io
import os
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def source_version():
    text = (ROOT / 'anvil' / '__init__.py').read_text(encoding='utf-8')
    match = re.search(r"^__version__\s*=\s*['\"]([0-9]+(?:\.[0-9]+)*)['\"]\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError('Expected a numeric dotted application version')
    return match.group(1)


def archive(entries, epoch):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        directories = set()
        for path in entries:
            parts = path.split('/')
            directories.update('/'.join(parts[:count]) for count in range(1, len(parts)))
        for path in sorted(directories):
            info = tarfile.TarInfo('./' + path + '/')
            info.type, info.mode, info.mtime = tarfile.DIRTYPE, 0o755, epoch
            tar.addfile(info)
        for path, (contents, mode) in sorted(entries.items()):
            info = tarfile.TarInfo('./' + path)
            info.size, info.mode, info.mtime = len(contents), mode, epoch
            tar.addfile(info, io.BytesIO(contents))
    compressed = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=compressed, mtime=epoch) as stream:
        stream.write(raw.getvalue())
    return compressed.getvalue()


def write_ar_member(stream, name, contents, epoch):
    header = (f"{name + '/':<16}{epoch:<12}{0:<6}{0:<6}"
              f"{'100644':<8}{len(contents):<10}`\n").encode('ascii')
    if len(header) != 60:
        raise ValueError('Invalid ar header; check SOURCE_DATE_EPOCH')
    stream.write(header)
    stream.write(contents)
    if len(contents) % 2:
        stream.write(b'\n')


SYSTEM_DEPENDS = 'python3 (>= 3.10), python3-pyside6.qtwidgets'
BUNDLED_DEPENDS = ('python3 (>= 3.10), python3 (<< 3.15), python3-venv, libc6 (>= 2.34), '
                   'libgl1, libegl1, libopengl0, libglib2.0-0 | libglib2.0-0t64, '
                   'libfontconfig1, libdbus-1-3, libxkbcommon0, libxkbcommon-x11-0, '
                   'libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, '
                   'libxcb-render-util0, libxcb-xinerama0, libxcb-xkb1, libxcb-shape0, '
                   'libxcb-sync1, libxcb-xfixes0, libxcb-randr0, libx11-xcb1, '
                   'libwayland-client0, libwayland-cursor0, libwayland-egl1')


def portable_entries(bundle):
    prefix = 'anvil-control-' + source_version() + '-linux-x86_64/'
    entries = {}
    with tarfile.open(bundle, 'r:gz') as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.startswith(prefix):
                raise ValueError('Unexpected portable archive member: ' + member.name)
            name = member.name[len(prefix):]
            if not name or '..' in Path(name).parts or Path(name).is_absolute():
                raise ValueError('Unsafe portable archive path')
            destination = 'usr/share/anvil-control/portable/' + name
            if destination in entries:
                raise ValueError('Duplicate portable archive path')
            # No incoming archive mode may introduce setuid or unexpected executables.
            entries[destination] = (archive.extractfile(member).read(), 0o755 if name == 'anvil-control' else 0o644)
    if 'usr/share/anvil-control/portable/SHA256SUMS' not in entries:
        raise ValueError('Portable archive has no checksum manifest')
    return entries


def build(output, epoch, bundle=None):
    version = source_version() + '~alpha1-1'
    entries = {
        'usr/bin/anvil-control': ((HERE / ('anvil-control-bundled' if bundle else 'anvil-control')).read_bytes(), 0o755),
        'usr/share/applications/io.anvil.Control.desktop':
            ((HERE / 'io.anvil.Control.desktop').read_bytes(), 0o644),
        'usr/share/icons/hicolor/scalable/apps/io.anvil.Control.svg':
            ((ROOT / 'packaging' / 'io.anvil.Control.svg').read_bytes(), 0o644),
        'usr/share/doc/anvil-control/copyright': ((ROOT / 'LICENSE').read_bytes(), 0o644),
    }
    if bundle:
        entries.update(portable_entries(bundle))
    else:
        for source in sorted((ROOT / 'anvil').glob('*.py')):
            if not source.is_file() or source.is_symlink():
                raise ValueError('Unexpected Python source: ' + str(source))
            entries['usr/share/anvil-control/anvil/' + source.name] = (source.read_bytes(), 0o644)
    installed_size = (sum(len(data) for data, _ in entries.values()) + 1023) // 1024
    control = (HERE / 'control.in').read_text(encoding='utf-8')
    control = control.replace('@VERSION@', version).replace('@INSTALLED_SIZE@', str(installed_size))
    control = control.replace('@ARCHITECTURE@', 'amd64' if bundle else 'all')
    control = control.replace('@DEPENDS@', BUNDLED_DEPENDS if bundle else SYSTEM_DEPENDS)
    with output.open('xb') as stream:
        stream.write(b'!<arch>\n')
        write_ar_member(stream, 'debian-binary', b'2.0\n', epoch)
        write_ar_member(stream, 'control.tar.gz', archive({'control': (control.encode(), 0o644)}, epoch), epoch)
        write_ar_member(stream, 'data.tar.gz', archive(entries, epoch), epoch)
    return output.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New .deb output path; refuses to overwrite')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--bundle', type=Path, help='Embed the matching offline portable archive (amd64)')
    mode.add_argument('--system-qt', action='store_true', help='Use distro python3-pyside6.qtwidgets (all architectures)')
    args = parser.parse_args()
    arch = 'amd64' if args.bundle else 'all'
    output = args.output or Path.cwd() / ('anvil-control_' + source_version() + '~alpha1-1_' + arch + '.deb')
    if output.suffix != '.deb':
        parser.error('Output path must end in .deb')
    try:
        epoch = int(os.environ.get('SOURCE_DATE_EPOCH', '0'))
    except ValueError:
        parser.error('SOURCE_DATE_EPOCH must be a nonnegative integer')
    if epoch < 0:
        parser.error('SOURCE_DATE_EPOCH must be a nonnegative integer')
    print(build(output, epoch, args.bundle))


if __name__ == '__main__':
    main()
