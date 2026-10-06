import unittest
import tempfile
import os
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from subprocess import CompletedProcess, TimeoutExpired
from anvil.backend import sensors, number, set_profile, property_value, cpu_temperature, is_asus_vendor, AmdGpu, Monitor, distribution, profile_names
from anvil.fans import supports_fan_write
from anvil.compat import capability_report


class BackendTests(unittest.TestCase):
    @patch('anvil.backend.platform.freedesktop_os_release', return_value={
        'PRETTY_NAME': 'Zorin OS 18', 'ID': 'zorin', 'VERSION_ID': '18'})
    def test_distribution_identity_uses_standard_os_release(self, release):
        self.assertEqual(distribution(), {'name': 'Zorin OS 18', 'id': 'zorin', 'version': '18'})

    @patch('anvil.backend.platform.freedesktop_os_release', side_effect=OSError)
    def test_distribution_fallback_handles_quotes_and_malformed_entries(self, release):
        with patch('anvil.backend.read', return_value='\n'.join([
                '# ignored', 'PRETTY_NAME="Deepin Linux"', 'ID=deepin',
                'VERSION_ID="25"', 'BROKEN="unfinished', 'NOT A KEY=ignored'])):
            self.assertEqual(distribution(), {'name': 'Deepin Linux', 'id': 'deepin', 'version': '25'})
        with patch('anvil.backend.read', return_value=''), patch('anvil.backend.platform.system', return_value='Linux'):
            self.assertEqual(distribution()['name'], 'Linux')

    def test_non_utf8_os_release_uses_available_fallback_without_abort(self):
        error = UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'invalid byte')
        with (patch('anvil.backend.platform.freedesktop_os_release', side_effect=error),
              patch('anvil.backend.read', side_effect=['', 'PRETTY_NAME="Fallback Linux"\nID=linux'])):
            self.assertEqual(distribution()['name'], 'Fallback Linux')

    def test_malformed_active_profile_json_is_normalized_before_reaching_ui(self):
        monitor = Monitor.__new__(Monitor)
        monitor.previous = None
        monitor.gpu = SimpleNamespace(sample=lambda: None)
        monitor.amd_gpu = SimpleNamespace(sample=lambda: None)
        for value in ([], {'data': 'balanced'}, 12, False, '', 'balanced'):
            with self.subTest(service_value=value), \
                 patch('anvil.backend.read', return_value=''), \
                 patch('anvil.backend.sensors', return_value=[]), \
                 patch('anvil.backend.run', return_value=json.dumps({'data': value})), \
                 patch('anvil.backend.shutil.disk_usage', return_value=SimpleNamespace(used=0, total=0)):
                sample = monitor.sample()
            self.assertEqual(sample['profile'], 'balanced' if value == 'balanced' else None)

    def test_missing_optional_tools_do_not_execute_discovery_commands(self):
        with (patch('anvil.backend.shutil.which', return_value=None),
              patch('anvil.backend.run') as execute):
            identity = Monitor.__new__(Monitor).discover()
        self.assertEqual(identity['pci'], '')
        self.assertIsNone(identity['openrgb'])
        self.assertIsNone(identity['tools']['busctl'])
        execute.assert_not_called()
        sample = {'sensors': [], 'profiles': [], 'gpu': None}
        rows = dict(capability_report(identity, sample, [], monitor_only=True)[1])
        self.assertIn('pciutils', rows['İsteğe bağlı araçlar'])

    def test_malformed_profile_service_data_does_not_allow_writes(self):
        malformed = [None, 'balanced', {'Profile': None}, {'Profile': {'data': 1}}]
        self.assertEqual(profile_names(malformed), [])
        self.assertEqual(profile_names({'Profile': {'data': 'balanced'}}), [])
        with patch('anvil.backend.property_value', return_value=malformed), patch('anvil.backend.subprocess.run') as execute:
            self.assertFalse(set_profile('balanced')[0])
        execute.assert_not_called()

    def test_missing_proc_metrics_leave_unknown_values_without_crash(self):
        monitor = Monitor.__new__(Monitor)
        monitor.previous = None
        monitor.gpu = SimpleNamespace(sample=lambda: None)
        monitor.amd_gpu = SimpleNamespace(sample=lambda: None)
        with patch('anvil.backend.read', return_value=''), \
             patch('anvil.backend.sensors', return_value=[]), \
             patch('anvil.backend.property_value', return_value=None), \
             patch('anvil.backend.shutil.disk_usage', return_value=SimpleNamespace(used=0, total=0)):
            sample = monitor.sample()
        self.assertIsNone(sample['cpu_usage'])
        self.assertIsNone(sample['memory_used'])
        self.assertIsNone(sample['memory_total'])

    def test_amdgpu_sysfs_telemetry_and_missing_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            driver = root/'drivers'/'amdgpu'
            driver.mkdir(parents=True)
            device = root/'drm'/'card0'/'device'
            device.mkdir(parents=True)
            (device/'driver').symlink_to(driver, target_is_directory=True)
            (device/'gpu_busy_percent').write_text('42')
            (device/'mem_info_vram_total').write_text('8192')
            (device/'mem_info_vram_used').write_text('2048')
            hw = device/'hwmon'/'hwmon0'
            hw.mkdir(parents=True)
            for name, value in [('name', 'amdgpu'), ('temp1_input', '61000'),
                                ('power1_average', '56000000'), ('fan1_input', '1250')]:
                (hw/name).write_text(value)
            gpu = AmdGpu(root/'drm').sample()
            self.assertEqual(gpu['temperature'], 61)
            self.assertEqual(gpu['usage'], 42)
            self.assertEqual(gpu['power'], 56)
            self.assertEqual(gpu['fan_rpm'], 1250)
            self.assertEqual(gpu['memory_total'], 8192)
            self.assertNotIn('fan', gpu)  # RPM must not be mislabeled as percent.
            (device/'gpu_busy_percent').write_text('999')
            (device/'mem_info_vram_used').write_text('99999')
            gpu = AmdGpu(root/'drm').sample()
            self.assertNotIn('usage', gpu)
            self.assertNotIn('memory_used', gpu)

    def test_intel_and_amd_cpu_sensor_drivers(self):
        readings = [
            {'chip':'coretemp', 'unit':'°C', 'value':44.0},
            {'chip':'k10temp', 'unit':'°C', 'value':51.5},
            {'chip':'acpitz', 'unit':'°C', 'value':90.0},
        ]
        self.assertEqual(cpu_temperature(readings), 51.5)
        self.assertIsNone(cpu_temperature([readings[2]]))

    def test_asus_vendor_detection_is_based_on_dmi_vendor(self):
        self.assertTrue(is_asus_vendor('ASUSTeK COMPUTER INC.'))
        self.assertTrue(is_asus_vendor('ASUS'))
        self.assertFalse(is_asus_vendor('Gigabyte Technology Co., Ltd.'))
        self.assertFalse(is_asus_vendor(''))

    def test_fan_writes_are_scoped_to_verified_board_profiles(self):
        self.assertTrue(supports_fan_write('PRIME H610M-K D4', 'ASUSTeK COMPUTER INC.'))
        self.assertFalse(supports_fan_write('PRIME H610M-K D4', 'Other vendor'))
        self.assertFalse(supports_fan_write('ROG STRIX X670E-E GAMING WIFI', 'ASUS'))

    def test_capabilities_are_detected_on_other_asus_models_without_writes(self):
        identity = {'board':'ROG STRIX X670E-E GAMING WIFI', 'vendor':'ASUSTeK COMPUTER INC.',
                    'asus':True, 'pwm':['/sys/class/hwmon/hwmon0/pwm1']}
        sample = {'sensors':[{'unit':'°C'}, {'unit':'RPM'}], 'gpu':None,
                  'profiles':[{'Profile':{'data':'balanced'}}]}
        overview, rows = capability_report(identity, sample, [])
        self.assertIn('ASUS anakart algılandı', overview)
        self.assertIn('Fan yazma: kapalı', overview)
        self.assertIn('henüz doğrulanmadı', dict(rows)['Anakart fan yazımı'])
        self.assertIn('görül', dict(rows)['PWM arayüzleri'])
        identity.update(board='PRIME H610M-K D4')
        overview, rows = capability_report(identity, sample, [1], helper_installed=False)
        self.assertIn('yardımcı gerekli', overview)
        self.assertIn('fan yardımcısı gerekli', dict(rows)['Anakart fan yazımı'])
        overview, rows = capability_report(identity, sample, [1], monitor_only=True)
        self.assertIn('Fan yazma: kapalı', overview)
        self.assertIn('yalnız izleme', dict(rows)['Anakart fan yazımı'])
        self.assertIn('değiştirme kapalı', dict(rows)['Güç profilleri'])
        identity['vendor'] = 'Other vendor'
        identity['asus'] = False
        self.assertIn('ASUS dışı', capability_report(identity, sample, [])[0])

    def test_missing_measurement_is_not_zero(self):
        self.assertIsNone(number('/path/that/does/not/exist'))

    def test_nonfinite_sysfs_measurements_are_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            reading = Path(directory) / 'fan1_input'
            for value in ('nan', 'inf', '-inf', '1e9999'):
                with self.subTest(value=value):
                    reading.write_text(value)
                    self.assertIsNone(number(reading))
            reading.write_text('1200')
            self.assertEqual(number(reading), 1200)

    def test_sensor_units_and_bad_reading(self):
        with tempfile.TemporaryDirectory() as d:
            hw = Path(d) / 'hwmon0'
            hw.mkdir()
            for name, value in {'name':'coretemp', 'temp1_label':'Package', 'temp1_input':'42500',
                                'fan1_input':'1200', 'temp2_input':'error',
                                'temp3_input':'nan', 'fan2_input':'inf'}.items():
                (hw/name).write_text(value)
            values = sensors(Path(d))
            self.assertEqual(len(values), 2)
            self.assertEqual(values[0]['value'], 42.5)
            self.assertEqual(values[1]['value'], 1200)

    def test_negative_fan_rpm_is_unavailable_but_zero_is_a_valid_readback(self):
        with tempfile.TemporaryDirectory() as d:
            hw = Path(d) / 'hwmon0'
            hw.mkdir()
            for name, value in {'name': 'example', 'fan1_input': '-1',
                                'fan2_input': '0', 'fan3_input': '1200',
                                'temp1_input': '-5000'}.items():
                (hw/name).write_text(value)
            values = sensors(Path(d))
            self.assertEqual([(item['unit'], item['value']) for item in values],
                             [('°C', -5), ('RPM', 0), ('RPM', 1200)])

    @patch('anvil.backend.run', return_value='')
    def test_unavailable_dbus(self, mocked):
        self.assertIsNone(property_value('Profiles'))

    @patch('anvil.backend.subprocess.run')
    @patch('anvil.backend.property_value', return_value=[{'Profile':{'data':'balanced'}}])
    def test_unknown_profile_never_executes(self, prop, execute):
        self.assertFalse(set_profile('invalid')[0])
        execute.assert_not_called()

    @patch('anvil.backend.subprocess.run')
    @patch('anvil.backend.property_value')
    def test_monitor_only_profile_never_reads_or_writes_dbus(self, prop, execute):
        with patch.dict(os.environ, {'ANVIL_MONITOR_ONLY': '1'}):
            ok, message = set_profile('balanced')
        self.assertFalse(ok)
        self.assertIn('yalnız izleme', message)
        prop.assert_not_called()
        execute.assert_not_called()

    @patch('anvil.backend.subprocess.run', return_value=CompletedProcess([], 0, '', ''))
    @patch('anvil.backend.property_value', side_effect=[[{'Profile':{'data':'balanced'}}], 'balanced'])
    def test_verified_profile_success(self, prop, execute):
        self.assertTrue(set_profile('balanced')[0])
        self.assertEqual(execute.call_args.args[0][-2:], ['s', 'balanced'])

    @patch('anvil.backend.subprocess.run', return_value=CompletedProcess([], 0, '', ''))
    @patch('anvil.backend.property_value', side_effect=[[{'Profile':{'data':'balanced'}}], 'performance'])
    def test_readback_mismatch_is_failure(self, prop, execute):
        self.assertFalse(set_profile('balanced')[0])

    @patch('anvil.backend.subprocess.run', return_value=CompletedProcess([], 1, '', 'Access denied'))
    @patch('anvil.backend.property_value', return_value=[{'Profile':{'data':'balanced'}}])
    def test_permission_denied(self, prop, execute):
        self.assertEqual(set_profile('balanced'), (False, 'Access denied'))

    @patch('anvil.backend.subprocess.run', side_effect=TimeoutExpired('busctl', 20))
    @patch('anvil.backend.property_value', return_value=[{'Profile':{'data':'balanced'}}])
    def test_timeout(self, prop, execute):
        self.assertFalse(set_profile('balanced')[0])

    @patch('anvil.backend.property_value', return_value=[{'Profile': {'data': 'balanced'}}])
    def test_profile_command_decode_error_returns_failure_for_worker(self, prop):
        error = UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'invalid byte')
        with patch('anvil.backend.subprocess.run', side_effect=error):
            success, message = set_profile('balanced')
        self.assertFalse(success)
        self.assertTrue(message)


if __name__ == '__main__':
    unittest.main()
