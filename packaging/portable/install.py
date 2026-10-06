#!/usr/bin/env python3
"""Prepare an offline, private Qt runtime; never changes system Python."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def verify_bundle(root=ROOT):
    for line in (root / 'SHA256SUMS').read_text(encoding='ascii').splitlines():
        digest, name = line.split('  ', 1)
        if not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise ValueError('Malformed bundle checksum')
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe bundle checksum path')
        source = root / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError('Missing bundle file: ' + name)
        actual = hashlib.sha256()
        with source.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                actual.update(chunk)
        if actual.hexdigest() != digest:
            raise ValueError('Bundle checksum mismatch: ' + name)


def check_runtime():
    if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'AMD64'):
        raise ValueError('This bundle requires Linux x86_64; use a native package on other architectures.')
    if not (3, 10) <= sys.version_info[:2] < (3, 15):
        raise ValueError('This bundle requires Python 3.10–3.14.')
    libc, version = platform.libc_ver()
    try:
        compatible = libc == 'glibc' and tuple(int(v) for v in version.split('.')[:2]) >= (2, 34)
    except ValueError:
        compatible = False
    if not compatible:
        raise ValueError('This bundle requires glibc 2.34 or newer; musl/Alpine is not supported.')


def runtime_directory(version):
    # Do not mix venvs between Python minor versions or application releases.
    return Path.home() / '.local' / 'share' / 'anvil-control' / 'runtime' / (version + '-py' + str(sys.version_info[0]) + '.' + str(sys.version_info[1]))


def prepare_runtime(version):
    target = runtime_directory(version)
    if target.is_symlink():
        raise ValueError('Runtime directory must not be a symbolic link.')
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (target / '.install.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        environment = target / 'venv'
        if environment.is_symlink():
            raise ValueError('Runtime venv must not be a symbolic link.')
        marker = target / '.requirements.sha256'
        signature = hashlib.sha256((ROOT / 'requirements.txt').read_bytes()).hexdigest()
        python = environment / 'bin' / 'python'
        ready = python.is_file() and marker.is_file() and marker.read_text() == signature
        if not ready:
            print('Preparing Anvil Control’s private Qt runtime (offline)…', flush=True)
            try:
                venv.EnvBuilder(with_pip=True).create(environment)
            except (subprocess.CalledProcessError, OSError) as exc:
                raise ValueError('Python venv/ensurepip is missing. On Debian/Ubuntu install python3-venv, then try again. ' + str(exc)) from exc
            subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
                            '--no-index', '--no-deps', '--require-hashes', '--find-links',
                            str(ROOT / 'wheels'), '-r', str(ROOT / 'requirements.txt')], check=True)
            subprocess.run([str(python), '-c', 'from PySide6 import QtCore, QtGui, QtWidgets'], check=True)
            marker.write_text(signature, encoding='ascii')
        return python


def desktop_entry():
    launcher = str(ROOT / 'anvil-control')
    # Desktop Entry quoting differs from shell quoting; escape reserved chars.
    quoted = launcher.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    icon = str(ROOT / 'io.anvil.Control.svg')
    return ('[Desktop Entry]\nType=Application\nName=Anvil Control (Portable)\n'
            'Comment=Linux hardware monitoring\nExec="' + quoted + '"\nIcon=' + icon +
            '\nTerminal=false\nCategories=System;Monitor;\nStartupWMClass=anvil-control\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify bundle and base runtime without installing')
    parser.add_argument('--desktop', action='store_true', help='Add a user-local application-menu entry')
    parser.add_argument('--run', action='store_true', help='Prepare the private runtime and start Anvil')
    args, application_args = parser.parse_known_args()
    try:
        check_runtime()
        verify_bundle()
        version = json.loads((ROOT / 'bundle.json').read_text())['version']
        if args.check:
            print('Bundle verified; Linux x86_64, Python and glibc requirements met.')
            return
        if os.geteuid() == 0:
            raise ValueError('Run Anvil as your desktop user, without sudo.')
        python = prepare_runtime(version)
        if args.desktop:
            directory = Path.home() / '.local' / 'share' / 'applications'
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / 'io.anvil.Control.Portable.desktop'
            target.write_text(desktop_entry(), encoding='utf-8')
            print('Application-menu entry: ' + str(target))
        if args.run:
            os.execv(str(python), [str(python), str(ROOT / 'run.py'), *application_args])
        print('Anvil Control is ready. Start it with ' + str(ROOT / 'anvil-control'))
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError) as exc:
        print('Anvil Control: ' + str(exc), file=sys.stderr)
        print('See README.md in this bundle for Linux GUI library requirements.', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
