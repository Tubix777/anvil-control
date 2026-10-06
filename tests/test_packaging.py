import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


debian = load('anvil_debian_builder', 'packaging/debian/build_deb.py')
portable = load('anvil_portable_builder', 'packaging/portable/build_bundle.py')
installer = load('anvil_portable_installer', 'packaging/portable/install.py')


def ar_members(contents):
    assert contents[:8] == b'!<arch>\n'
    offset, result = 8, {}
    while offset < len(contents):
        header = contents[offset:offset + 60]
        size = int(header[48:58])
        name = header[:16].decode().strip().removesuffix('/')
        result[name] = contents[offset + 60:offset + 60 + size]
        offset += 60 + size + size % 2
    return result


class PackagingTests(unittest.TestCase):
    def test_native_deb_is_deterministic_and_has_no_privileged_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            one, two = Path(directory) / 'one.deb', Path(directory) / 'two.deb'
            debian.build(one, 0)
            debian.build(two, 0)
            self.assertEqual(one.read_bytes(), two.read_bytes())
            members = ar_members(one.read_bytes())
            self.assertEqual(members['debian-binary'], b'2.0\n')
            with tarfile.open(fileobj=io.BytesIO(members['control.tar.gz'])) as archive:
                control = archive.extractfile('./control').read().decode()
                self.assertIn('Architecture: all', control)
                self.assertIn('Version: ' + debian.source_version() + '~alpha1-1', control)
                self.assertIn('python3-pyside6.qtwidgets', control)
                self.assertEqual(len(archive.getmembers()), 1)
            with tarfile.open(fileobj=io.BytesIO(members['data.tar.gz'])) as archive:
                paths = archive.getnames()
                self.assertTrue(any(path.endswith('/anvil/launcher.py') for path in paths))
                self.assertFalse(any('helper' in path or 'polkit' in path or 'modules-load' in path for path in paths))
            with self.assertRaises(FileExistsError):
                debian.build(one, 0)

    def test_portable_archive_checksums_detect_modified_application(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (patch.object(portable, 'obtain_wheel', side_effect=lambda package, _cache:
                               (portable.WHEELS[package][0], b'fixture-wheel-' + package.encode())),
                  patch.object(portable, 'upstream_licenses', return_value={'licenses/QtForPython/LGPL-3.0-only.txt': (b'fixture-license', 0o644)})):
                entries = portable.bundle_entries(root)
            for name, (contents, _) in entries.items():
                output = root / name
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(contents)
            installer.verify_bundle(root)
            target = root / 'app' / 'anvil' / 'app.py'
            target.write_bytes(target.read_bytes() + b'\n# accidental modification\n')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                installer.verify_bundle(root)

    def test_bundled_deb_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / 'unsafe.tar.gz'
            with tarfile.open(archive_path, 'w:gz') as archive:
                info = tarfile.TarInfo('anvil-control-' + debian.source_version() + '-linux-x86_64/../escape')
                info.size = 1
                archive.addfile(info, io.BytesIO(b'x'))
            with self.assertRaisesRegex(ValueError, 'Unsafe portable archive path'):
                debian.portable_entries(archive_path)

    def test_private_runtime_is_separate_for_each_python_minor(self):
        with patch.object(installer.sys, 'version_info', (3, 10)), patch.object(installer.Path, 'home', return_value=Path('/home/example')):
            self.assertEqual(installer.runtime_directory('0.14.0'), Path('/home/example/.local/share/anvil-control/runtime/0.14.0-py3.10'))
        with patch.object(installer.sys, 'version_info', (3, 13)), patch.object(installer.Path, 'home', return_value=Path('/home/example')):
            self.assertNotEqual(installer.runtime_directory('0.14.0').name, '0.14.0-py3.10')

    def test_runtime_rejects_unsupported_python_and_musl_before_install(self):
        with patch.object(installer.platform, 'machine', return_value='x86_64'), patch.object(installer.sys, 'version_info', (3, 15)):
            with self.assertRaisesRegex(ValueError, 'Python 3.10'):
                installer.check_runtime()
        with patch.object(installer.platform, 'machine', return_value='x86_64'), patch.object(installer.sys, 'version_info', (3, 12)), patch.object(installer.platform, 'libc_ver', return_value=('musl', '1.2')):
            with self.assertRaisesRegex(ValueError, 'glibc 2.34'):
                installer.check_runtime()


if __name__ == '__main__':
    unittest.main()
