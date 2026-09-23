import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from anvil.rgb import parse_devices
from anvil.fans import fan_result, channels, FAN_PRESETS, preset_points

path = Path(__file__).resolve().parents[1]/'packaging/anvil-fan-helper'
loader = importlib.machinery.SourceFileLoader('fan_helper', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)
CURVE = [[30, 50], [45, 60], [60, 75], [75, 100], [85, 100]]


class FanTests(unittest.TestCase):
    def test_safe_preset_curves_are_distinct_and_independently_validated(self):
        self.assertEqual(set(FAN_PRESETS), {'calm', 'balanced', 'cool'})
        first_point_speeds = []
        for key in FAN_PRESETS:
            points = preset_points(key)
            self.assertEqual(helper.validate_curve(points), points)
            first_point_speeds.append(points[0][1])
            points[0][1] = 99
            self.assertNotEqual(preset_points(key)[0][1], 99)
        self.assertEqual(first_point_speeds, sorted(first_point_speeds))
        self.assertIsNone(preset_points('unknown'))

    def test_only_complete_peci_pwm_channel_is_offered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = root/'hwmon0'
            hw.mkdir()
            (hw/'name').write_text('nct6798')
            for name, value in [('pwm1_enable', '5'), ('pwm1_mode', '1'),
                                ('pwm1_temp_sel', '8'), ('temp8_label', 'PECI Agent 0'),
                                ('temp8_input', '40000')]:
                (hw/name).write_text(value)
            for i in range(1, 6):
                (hw/f'pwm1_auto_point{i}_temp').write_text(str(i*10000))
                (hw/f'pwm1_auto_point{i}_pwm').write_text(str(i*40))
            self.assertEqual([item['channel'] for item in channels(root, 'PRIME H610M-K D4', 'ASUS')], [1])
            (hw/'temp8_label').write_text('CPUTIN')
            self.assertEqual(channels(root, 'PRIME H610M-K D4', 'ASUS'), [])
            (hw/'temp8_label').write_text('PECI Agent 0')
            (hw/'pwm1_auto_point5_temp').unlink()
            self.assertEqual(channels(root, 'PRIME H610M-K D4', 'ASUS'), [])
            self.assertEqual(channels(root, 'OTHER BOARD', 'ASUS'), [])
            self.assertEqual(channels(root, 'PRIME H610M-K D4', 'Other vendor'), [])

    def test_ui_accepts_only_matching_verified_helper_result(self):
        fields = {'pwm1_enable': 0}
        for i in range(1, 6):
            fields[f'pwm1_auto_point{i}_temp'] = i*10000
            fields[f'pwm1_auto_point{i}_pwm'] = i*50
        response = {'ok': True, 'action': 'full', 'channel': 1, 'verified': fields}
        self.assertTrue(fan_result(True, json.dumps(response), '', 'full', 1)[0])
        self.assertFalse(fan_result(True, json.dumps(response), '', 'curve', 1)[0])
        self.assertFalse(fan_result(True, '{}', '', 'full', 1)[0])
        self.assertFalse(fan_result(False, '', 'permission denied', 'full', 1)[0])

    def test_validation(self):
        self.assertEqual(helper.validate_curve(CURVE), CURVE)
        for invalid in [[], [[30, 0]]*5, [[30, 50], [20, 60], [60, 75], [75, 100], [85, 100]],
                        [[30, 50], [45, 60], [60, 75], [75, 80], [85, 100]]]:
            with self.assertRaises(ValueError):
                helper.validate_curve(invalid)

    def fixture(self, root):
        hw = root/'hwmon'
        hw.mkdir()
        fields = {'pwm1_enable':5, 'pwm1_mode':1, 'pwm1_temp_sel':8,
                  'temp8_label':'PECI Agent 0 Calibration', 'temp8_input':40000}
        for i in range(1, 6):
            fields[f'pwm1_auto_point{i}_temp'] = 20000*i
            fields[f'pwm1_auto_point{i}_pwm'] = min(255, i*51)
        for key, value in fields.items():
            (hw/key).write_text(str(value))
        return hw

    def test_curve_full_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = self.fixture(root)
            before = {p.name:p.read_text() for p in hw.iterdir()}
            result = helper.transact(hw, 1, 'curve', CURVE, root/'state')
            self.assertTrue(result['ok'])
            self.assertEqual((hw/'pwm1_auto_point5_temp').read_text(), '85000')
            self.assertEqual((hw/'pwm1_auto_point1_pwm').read_text(), '128')
            helper.transact(hw, 1, 'full', None, root/'state')
            self.assertEqual((hw/'pwm1_enable').read_text(), '0')
            helper.transact(hw, 1, 'restore', None, root/'state')
            self.assertEqual({p.name:p.read_text() for p in hw.iterdir()}, before)

    def test_wrong_source_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = self.fixture(root)
            (hw/'temp8_label').write_text('CPUTIN')
            with self.assertRaises(ValueError):
                helper.transact(hw, 1, 'full', None, root/'state')
            self.assertEqual((hw/'pwm1_enable').read_text(), '5')

    def test_failed_curve_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = self.fixture(root)
            before = {p.name:p.read_text() for p in hw.iterdir()}
            original = Path.write_text
            failed = [False]
            def write(path, data, *args, **kwargs):
                if path.name == 'pwm1_auto_point2_temp' and not failed[0]:
                    failed[0] = True
                    raise OSError('simulated I/O failure')
                return original(path, data, *args, **kwargs)
            with patch.object(Path, 'write_text', write), self.assertRaises(OSError):
                helper.transact(hw, 1, 'curve', CURVE, root/'state')
            self.assertEqual({p.name:p.read_text() for p in hw.iterdir()}, before)

    def test_rgb_modes(self):
        devices = parse_devices('Connection attempt failed\n0: Kingston Fury\n  Modes: [Direct] Static "Color Cycle"\n')
        self.assertEqual(devices[0]['modes'], ['Direct', 'Static', 'Color Cycle'])
