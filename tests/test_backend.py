import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess, TimeoutExpired
from anvil.backend import sensors, number, set_profile, property_value, cpu_temperature, is_asus_vendor
from anvil.fans import supports_fan_write


class BackendTests(unittest.TestCase):
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
        self.assertTrue(supports_fan_write('PRIME H610M-K D4'))
        self.assertFalse(supports_fan_write('ROG STRIX X670E-E GAMING WIFI'))

    def test_missing_measurement_is_not_zero(self):
        self.assertIsNone(number('/path/that/does/not/exist'))

    def test_sensor_units_and_bad_reading(self):
        with tempfile.TemporaryDirectory() as d:
            hw = Path(d) / 'hwmon0'
            hw.mkdir()
            for name, value in {'name':'coretemp', 'temp1_label':'Package', 'temp1_input':'42500',
                                'fan1_input':'1200', 'temp2_input':'error'}.items():
                (hw/name).write_text(value)
            values = sensors(Path(d))
            self.assertEqual(len(values), 2)
            self.assertEqual(values[0]['value'], 42.5)
            self.assertEqual(values[1]['value'], 1200)

    @patch('anvil.backend.run', return_value='')
    def test_unavailable_dbus(self, mocked):
        self.assertIsNone(property_value('Profiles'))

    @patch('anvil.backend.subprocess.run')
    @patch('anvil.backend.property_value', return_value=[{'Profile':{'data':'balanced'}}])
    def test_unknown_profile_never_executes(self, prop, execute):
        self.assertFalse(set_profile('invalid')[0])
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


if __name__ == '__main__':
    unittest.main()
