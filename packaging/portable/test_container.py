#!/usr/bin/env python3
"""Install and GUI-smoke a release in a disposable Podman container.

This changes only the named throwaway container. No host packages or hardware
settings are changed. Images are explicit arguments, not inferred derivatives.
"""
import argparse
from pathlib import Path
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
GUI_DEPENDENCIES = ['python3-venv', 'libgl1', 'libegl1', 'libopengl0', 'libglib2.0-0',
                    'libfontconfig1', 'libdbus-1-3', 'libxkbcommon0', 'libxkbcommon-x11-0',
                    'libxcb-cursor0', 'libxcb-icccm4', 'libxcb-image0', 'libxcb-keysyms1',
                    'libxcb-render-util0', 'libxcb-xinerama0', 'libxcb-xkb1', 'libxcb-shape0',
                    'libxcb-sync1', 'libxcb-xfixes0', 'libxcb-randr0', 'libx11-xcb1',
                    'libwayland-client0', 'libwayland-cursor0', 'libwayland-egl1']


def command(*args):
    subprocess.run(list(args), check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, help='Explicit Debian/Ubuntu-family image tag or digest')
    parser.add_argument('--artifact', type=Path, required=True, help='Built DEB or portable .tar.gz')
    parser.add_argument('--smoke', type=Path, default=ROOT / 'tests' / 'smoke_portable.py')
    args = parser.parse_args()
    artifact = args.artifact.resolve(strict=True)
    name = 'anvil-package-test-' + uuid.uuid4().hex[:12]
    try:
        command('podman', 'run', '-d', '--name', name, args.image, 'sleep', 'infinity')
        command('podman', 'inspect', '--format', '{{.ImageName}} {{.Image}}', name)
        command('podman', 'cp', str(artifact), name + ':/tmp/release' + ('.deb' if artifact.suffix == '.deb' else '.tar.gz'))
        command('podman', 'cp', str(args.smoke.resolve(strict=True)), name + ':/tmp/smoke.py')
        command('podman', 'exec', name, 'apt-get', 'update', '-qq')
        command('podman', 'exec', '-e', 'DEBIAN_FRONTEND=noninteractive', name,
                'apt-get', 'install', '-y', '-qq', 'xvfb', 'xauth', 'pciutils')
        command('podman', 'exec', name, 'useradd', '-m', '-u', '17014', 'anvil-test')
        if artifact.suffix == '.deb':
            command('podman', 'exec', name, 'dpkg-deb', '--info', '/tmp/release.deb')
            command('podman', 'exec', '-e', 'DEBIAN_FRONTEND=noninteractive', name,
                    'apt-get', 'install', '-y', '-qq', '/tmp/release.deb')
            # Bundled and system-Qt variants have distinct application locations.
            bundle = '/usr/share/anvil-control/portable'
            probe = subprocess.run(['podman', 'exec', name, 'test', '-f', bundle + '/install.py'])
            portable = probe.returncode == 0
            app_path = bundle + '/app' if portable else '/usr/share/anvil-control'
        elif str(artifact).endswith('.tar.gz'):
            command('podman', 'exec', '-e', 'DEBIAN_FRONTEND=noninteractive', name,
                    'apt-get', 'install', '-y', '-qq', *GUI_DEPENDENCIES)
            command('podman', 'exec', name, 'mkdir', '-p', '/opt/anvil')
            command('podman', 'exec', name, 'tar', '-xzf', '/tmp/release.tar.gz',
                    '-C', '/opt/anvil', '--strip-components=1')
            bundle, portable, app_path = '/opt/anvil', True, '/opt/anvil/app'
        else:
            parser.error('Artifact must be a DEB or portable .tar.gz')
        base = ['podman', 'exec', '--user', 'anvil-test', '-e', 'HOME=/home/anvil-test', name]
        if portable:
            command(*base, 'python3', bundle + '/install.py', '--check')
            command(*base, 'python3', bundle + '/install.py', '--desktop')
            runtime = subprocess.check_output([*base, 'python3', '-c',
                'import json,sys;from pathlib import Path;'
                'v=json.loads(Path("' + bundle + '/bundle.json").read_text())["version"];'
                'print("/home/anvil-test/.local/share/anvil-control/runtime/"+v+"-py"+'
                'str(sys.version_info[0])+"."+str(sys.version_info[1])+"/venv/bin/python")'], text=True).strip()
        else:
            runtime = '/usr/bin/python3'
            command('podman', 'exec', '-e', 'DEBIAN_FRONTEND=noninteractive', name,
                    'apt-get', 'install', '-y', '-qq', 'python3-pyside6.qttest')
        for plugin in ('offscreen', 'xcb'):
            command(*base, 'env', 'PYTHONPATH=' + app_path, 'QT_QPA_PLATFORM=' + plugin,
                    'xvfb-run', '-a', runtime, '/tmp/smoke.py')
        print('PASS: ' + args.image + ' installation and offscreen/X11 monitoring launch')
    finally:
        subprocess.run(['podman', 'rm', '-f', name], check=False)


if __name__ == '__main__':
    main()
