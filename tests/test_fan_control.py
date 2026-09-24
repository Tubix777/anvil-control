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

    def test_curve_success_requires_exact_requested_temperature_and_pwm_readback(self):
        fields = {'pwm1_enable': 5}
        for index, (temp, speed) in enumerate(CURVE, 1):
            fields[f'pwm1_auto_point{index}_temp'] = temp * 1000
            fields[f'pwm1_auto_point{index}_pwm'] = round(speed * 255 / 100)
        response = {'ok': True, 'action': 'curve', 'channel': 1, 'verified': fields}
        output = json.dumps(response)
        self.assertTrue(fan_result(True, output, '', 'curve', 1, CURVE)[0])
        self.assertFalse(fan_result(True, output, '', 'curve', 1)[0])
        for key in ('pwm1_auto_point2_temp', 'pwm1_auto_point3_pwm'):
            with self.subTest(key=key):
                changed = dict(fields)
                changed[key] += 1
                result = fan_result(True, json.dumps(dict(response, verified=changed)),
                                    '', 'curve', 1, CURVE)
                self.assertFalse(result[0])
                self.assertIn('istenen noktalarla uyuşmuyor', result[1])

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

    def test_channel_reports_source_and_optional_ramp_times(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = self.fixture(root)
            (hw/'name').write_text('nct6798')
            (hw/'fan1_input').write_text('1420')
            (hw/'pwm1_step_up_time').write_text('500')
            (hw/'pwm1_step_down_time').write_text('1500')

            item, = channels(root, 'PRIME H610M-K D4', 'ASUS')
            self.assertEqual(item['channel'], 1)
            self.assertEqual(item['source_label'], 'PECI Agent 0 Calibration')
            self.assertEqual(item['source_temp'], 40.0)
            self.assertEqual(item['step_up_ms'], 500.0)
            self.assertEqual(item['step_down_ms'], 1500.0)

            (hw/'pwm1_step_up_time').unlink()
            (hw/'pwm1_step_down_time').unlink()
            item, = channels(root, 'PRIME H610M-K D4', 'ASUS')
            self.assertIsNone(item['step_up_ms'])
            self.assertIsNone(item['step_down_ms'])
            self.assertEqual(item['source_temp'], 40.0)

    def test_optional_secondary_source_never_hides_an_otherwise_valid_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = self.fixture(root)
            (hw/'name').write_text('nct6798')
            for path in list(hw.glob('pwm1_*')):
                (hw/path.name.replace('pwm1_', 'pwm2_', 1)).write_text(path.read_text())

            def selected():
                items = channels(root, 'PRIME H610M-K D4', 'ASUS')
                self.assertEqual([item['channel'] for item in items], [1, 2])
                self.assertNotIn('secondary_source', items[0])
                return items[1]

            self.assertNotIn('secondary_source', selected())
            selection = hw/'pwm2_weight_temp_sel'
            selection.write_text('0')
            self.assertEqual(selected()['secondary_source'], {'status': 'off'})

            selection.write_text('6')
            (hw/'temp6_label').write_text('System')
            (hw/'temp6_input').write_text('35500')
            self.assertEqual(selected()['secondary_source'],
                             {'status': 'selected', 'index': 6, 'label': 'System', 'temp': 35.5})
            for bad_temp in ('NaN', '128000'):
                with self.subTest(bad_temp=bad_temp):
                    (hw/'temp6_input').write_text(bad_temp)
                    self.assertIsNone(selected()['secondary_source']['temp'])
            (hw/'temp6_input').unlink()
            self.assertIsNone(selected()['secondary_source']['temp'])

            for bad_selection in ('not-a-number', '-1', '999'):
                with self.subTest(bad_selection=bad_selection):
                    selection.write_text(bad_selection)
                    self.assertEqual(selected()['secondary_source'], {'status': 'unreadable'})
            selection.unlink()
            self.assertNotIn('secondary_source', selected())

    def test_ambiguous_controller_identity_never_offers_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = self.fixture(root)
            (hw/'name').write_text('nct6798')
            duplicate = root/'hwmon2'
            duplicate.mkdir()
            for item in hw.iterdir():
                (duplicate/item.name).write_text(item.read_text())
            self.assertEqual(channels(root, 'PRIME H610M-K D4', 'ASUS'), [])
            (duplicate/'name').write_text('coretemp')
            self.assertEqual([item['channel'] for item in channels(root, 'PRIME H610M-K D4', 'ASUS')], [1])

    def test_malformed_readback_never_offers_a_write_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = self.fixture(root)
            (hw/'name').write_text('nct6798')
            for name, bad_value in [
                ('temp8_input', 'NaN'), ('temp8_input', '-1000'),
                ('temp8_input', '110000'),
                ('pwm1_auto_point1_temp', 'NaN'),
                ('pwm1_auto_point2_temp', 'not-a-number'),
                ('pwm1_auto_point3_temp', '-1'),
                ('pwm1_auto_point4_temp', '127001'),
                ('pwm1_auto_point5_pwm', 'inf'),
                ('pwm1_auto_point5_pwm', '256'),
            ]:
                path = hw/name
                original = path.read_text()
                with self.subTest(name=name, bad_value=bad_value):
                    path.write_text(bad_value)
                    self.assertEqual(channels(root, 'PRIME H610M-K D4', 'ASUS'), [])
                path.write_text(original)

            # A real BIOS critical point may follow a higher fourth threshold.
            (hw/'pwm1_auto_point4_temp').write_text('100000')
            (hw/'pwm1_auto_point5_temp').write_text('85000')
            item, = channels(root, 'PRIME H610M-K D4', 'ASUS')
            self.assertEqual(item['points'][3][0], 100.0)
            self.assertEqual(item['points'][4][0], 85.0)

            for suffix in ('enable', 'mode', 'temp_sel'):
                (hw/f'pwm2_{suffix}').write_text((hw/f'pwm1_{suffix}').read_text())
            for i in range(1, 6):
                for suffix in ('temp', 'pwm'):
                    (hw/f'pwm2_auto_point{i}_{suffix}').write_text(
                        (hw/f'pwm1_auto_point{i}_{suffix}').read_text())
            (hw/'pwm2_auto_point5_temp').write_text('125000')
            self.assertEqual([item['channel'] for item in channels(root, 'PRIME H610M-K D4', 'ASUS')], [1, 2])
            (hw/'pwm1_auto_point1_temp').write_text('NaN')
            self.assertEqual([item['channel'] for item in channels(root, 'PRIME H610M-K D4', 'ASUS')], [2])

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
