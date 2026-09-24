"""Read-only fan display tests; no privileged helper or hardware writes."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QSettings
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QLabel

from anvil.app import (Window, configure_style, fan_channel_label,
                       hardware_fan_curve_text, preferred_fan_channel)
from anvil.fans import channels


def channel(number, rpm, points=None, mode='5'):
    return dict(channel=number, rpm=rpm, mode=mode,
                points=points or [[20, 20], [35, 35], [50, 50], [65, 70], [70, 100]],
                source_label='PECI Agent 0', source_temp=31,
                step_up_ms=0, step_down_ms=0)


class FanUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        configure_style(cls.app)

    def test_only_one_spinning_channel_is_preferred_without_socket_guess(self):
        items = [channel(1, 0), channel(2, 1400)]
        self.assertEqual(preferred_fan_channel(items), 2)
        self.assertEqual(preferred_fan_channel(items, 1), 1)
        self.assertEqual(preferred_fan_channel([channel(1, 500), channel(2, 1400)]), 1)
        self.assertEqual(preferred_fan_channel([channel(1, 0), channel(2, 0)]), 1)
        self.assertIsNone(preferred_fan_channel([]))
        self.assertEqual(fan_channel_label(items[0]), 'Kanal 1 · 0 RPM')
        self.assertEqual(fan_channel_label(items[1]), 'Kanal 2 · 1400 RPM')
        self.assertIn('RPM okunamadı', fan_channel_label(channel(2, None)))

    def test_hardware_curve_source_and_inactive_mode_are_explicit(self):
        current = hardware_fan_curve_text(channel(2, 1400))
        self.assertIn('Donanımdan okunan etkin otomatik eğri', current)
        self.assertIn('20 °C → ≈%20', current)
        self.assertIn('Kritik eşik: 70 °C · okunan kritik PWM ≈%100', current)
        self.assertIn('PECI Agent 0 31 °C', current)
        self.assertIn('hızlanma 0 ms / yavaşlama 0 ms', current)
        self.assertIn('gecikme yok', current)
        inactive = hardware_fan_curve_text(channel(2, 1400, mode='0'))
        self.assertIn('şu an tam hız etkin', inactive)
        self.assertNotIn('etkin otomatik eğri', inactive)
        broken = channel(2, 1400, points=[[20, None]])
        self.assertIn('beş noktanın tamamı okunamadı', hardware_fan_curve_text(broken))
        self.assertIn('yalnızca önizlemedir', hardware_fan_curve_text(None))

    def test_critical_threshold_is_separate_from_normal_curve_slopes(self):
        unusual = channel(2, 1400, points=[[20, 20], [35, 35], [50, 50], [100, 80], [85, 70]])
        text = hardware_fan_curve_text(unusual)
        self.assertIn('100 °C → ≈%80', text)
        self.assertIn('Kritik eşik: 85 °C · okunan kritik PWM ≈%70', text)
        self.assertNotIn('85 °C → ≈%70', text)
        self.assertNotIn('tam hız', text)

    def test_optional_secondary_source_is_not_mistaken_for_active_fan_control(self):
        first = channel(1, 500)
        self.assertNotIn('İkincil', hardware_fan_curve_text(first))
        second = channel(2, 1400)
        second['secondary_source'] = {'status': 'off'}
        self.assertIn('devre dışı/atanmamış (0)', hardware_fan_curve_text(second))
        second['secondary_source'] = {'status': 'unreadable'}
        self.assertIn('seçim okunamadı', hardware_fan_curve_text(second))
        second['secondary_source'] = {'status': 'selected', 'index': 6,
                                      'label': 'System', 'temp': 35.5}
        self.assertIn('İkincil kaynak seçimi: System (35.5 °C)', hardware_fan_curve_text(second))
        second['secondary_source']['temp'] = None
        self.assertIn('System (sıcaklık okunamadı)', hardware_fan_curve_text(second))
        second['mode'] = '0'
        self.assertIn('tam hız modunda otomatik kontrol etkin değil',
                      hardware_fan_curve_text(second))

    def test_selection_and_live_readback_follow_selected_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                sample = dict(time=0, cpu_usage=None, cpu_temp=None, cpu_mhz=None,
                              memory_used=None, memory_total=None, disk_used=0, disk_total=0,
                              uptime='', sensors=[], gpu={}, profile=None, profiles=[])
                items = [channel(1, 0, [[20, 20], [35, 35], [50, 50], [65, 70], [70, 100]]),
                         channel(2, 1400, [[20, 30], [35, 40], [50, 55], [65, 80], [70, 100]])]
                with patch('anvil.app.channels', return_value=items), patch('anvil.app.Path.exists', return_value=False):
                    window.update_data(sample)
                self.assertTrue(window.fan_channel.isEnabled())
                self.assertTrue(all(not control.isEnabled() for control in window.fan_controls))
                self.assertEqual(window.fan_channel.currentData(), 2)
                self.assertEqual(window.fan_channel.itemText(0), 'Kanal 1 · 0 RPM')
                self.assertEqual(window.fan_channel.itemText(1), 'Kanal 2 · 1400 RPM')
                self.assertIn('20 °C → ≈%30', window.fan_curve_info.text())
                window.fan_channel.setCurrentIndex(0)
                self.assertIn('20 °C → ≈%20', window.fan_curve_info.text())
                with (patch('anvil.app.channels', return_value=items),
                      patch('anvil.app.Path.exists', return_value=True),
                      patch.object(window, 'hardware_busy', return_value=True)):
                    window.update_data(sample)
                self.assertTrue(window.fan_channel.isEnabled())
                self.assertTrue(all(not control.isEnabled() for control in window.fan_controls))
                changed = [channel(1, 502), channel(2, 1391)]
                with patch('anvil.app.channels', return_value=changed):
                    window.update_data(sample)
                self.assertEqual(window.fan_channel.currentData(), 1)
                self.assertEqual(window.fan_channel.itemText(0), 'Kanal 1 · 502 RPM')
                self.assertEqual(window.fan_channel.itemText(1), 'Kanal 2 · 1391 RPM')
                with patch('anvil.app.channels', return_value=[]):
                    window.update_data(sample)
                self.assertIsNone(window.fan_channel.currentData())
                self.assertIn('yalnızca önizlemedir', window.fan_curve_info.text())
            finally:
                window.quit_app()

    def test_unsupported_asus_board_does_not_offer_hardware_curve_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = root/'hwmon0'
            hw.mkdir()
            for name, value in [('name', 'nct6798'), ('pwm1_enable', '5'),
                                ('pwm1_mode', '1'), ('pwm1_temp_sel', '8'),
                                ('temp8_label', 'PECI Agent 0'), ('temp8_input', '40000')]:
                (hw/name).write_text(value)
            for index in range(1, 6):
                (hw/f'pwm1_auto_point{index}_temp').write_text(str(index * 10000))
                (hw/f'pwm1_auto_point{index}_pwm').write_text(str(index * 40))
            vendor = 'ASUSTeK COMPUTER INC.'
            board = 'ROG STRIX B650E-F GAMING WIFI'
            self.assertEqual(len(channels(root, 'PRIME H610M-K D4', vendor)), 1)
            self.assertEqual(channels(root, board, vendor), [])

            settings = QSettings(str(root/'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                window.monitor.identity.update(board=board, vendor=vendor, asus=True)
                sample = dict(time=100.0, cpu_usage=None, cpu_temp=None, cpu_mhz=None,
                              memory_used=None, memory_total=None, disk_used=0, disk_total=0,
                              uptime='', sensors=[], gpu={}, profile=None, profiles=[])
                with patch('anvil.app.channels', return_value=channels(root, board, vendor)):
                    window.update_data(sample)
                self.assertFalse(window.fan_channel.isEnabled())
                self.assertIsNone(window.fan_channel.currentData())
                self.assertTrue(all(not control.isEnabled() for control in window.fan_controls))
                self.assertIn('donanım eğrisi okunamıyor', window.fan_curve_info.text())
                self.assertIn('yalnızca önizlemedir', window.fan_curve_info.text())
                self.assertNotIn('Donanımdan okunan', window.fan_curve_info.text())
                self.assertIn('mevcut donanım eğrisi gösterilmez', window.fan_feedback.text())
                self.assertNotIn('Hız eğrilerini inceleyebilirsiniz', window.fan_feedback.text())
            finally:
                window.quit_app()

    def test_screen_reader_names_follow_live_curve_and_rpm_text(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                curve = QAccessible.queryAccessibleInterface(window.fan_curve_info)
                trend = QAccessible.queryAccessibleInterface(window.fan_trend_info)
                self.assertEqual(curve.text(QAccessible.Text.Description),
                                 'Seçili fan kanalının donanım eğrisi')
                self.assertEqual(trend.text(QAccessible.Text.Description),
                                 'Seçili fan kanalının son devir değişimi')
                sample = dict(time=100.0, cpu_usage=None, cpu_temp=None, cpu_mhz=None,
                              memory_used=None, memory_total=None, disk_used=0, disk_total=0,
                              uptime='', sensors=[], gpu={}, profile=None, profiles=[])
                items = [channel(1, 500), channel(2, 1400)]
                with patch('anvil.app.channels', return_value=items):
                    window.update_data(sample)
                self.assertEqual(curve.text(QAccessible.Text.Name), window.fan_curve_info.text())
                self.assertEqual(trend.text(QAccessible.Text.Name), window.fan_trend_info.text())
                window.fan_channel.setCurrentIndex(1)
                self.assertIn('Kanal 2', curve.text(QAccessible.Text.Name))
                self.assertIn('1400 RPM', trend.text(QAccessible.Text.Name))
                window.on_error('örnek hata')
                self.assertIn('güncel olmayabilir', curve.text(QAccessible.Text.Name))
                self.assertIn('Ölçüm yenilenemedi', trend.text(QAccessible.Text.Name))
            finally:
                window.quit_app()

    def test_recent_rpm_change_follows_selected_channel_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                sample = dict(time=100.0, cpu_usage=None, cpu_temp=None, cpu_mhz=None,
                              memory_used=None, memory_total=None, disk_used=0, disk_total=0,
                              uptime='', sensors=[], gpu={}, profile=None, profiles=[])
                with patch('anvil.app.channels', return_value=[channel(1, 500), channel(2, 1400)]):
                    window.update_data(sample)
                self.assertEqual(window.fan_channel.currentData(), 1)
                self.assertIn('500 RPM', window.fan_trend_info.text())
                window.fan_channel.setCurrentIndex(1)
                self.assertIn('1400 RPM', window.fan_trend_info.text())
                with patch('anvil.app.channels', return_value=[channel(1, 900), channel(2, 1300)]):
                    window.update_data(dict(sample, time=102.0))
                self.assertIn('1300–1400 RPM', window.fan_trend_info.text())
                self.assertIn('100 RPM / 2 sn', window.fan_trend_info.text())
                window.fan_channel.setCurrentIndex(0)
                self.assertIn('500–900 RPM', window.fan_trend_info.text())
                self.assertIn('+400 RPM / 2 sn', window.fan_trend_info.text())
                with patch('anvil.app.channels', return_value=[]):
                    window.update_data(dict(sample, time=104.0))
                self.assertIsNone(window.fan_channel.currentData())
                self.assertIn('fan kanalı seçin', window.fan_trend_info.text())
            finally:
                window.quit_app()

    def test_paused_and_failed_samples_never_look_live_in_fan_panel(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                sample = dict(time=100.0, cpu_usage=None, cpu_temp=None, cpu_mhz=None,
                              memory_used=None, memory_total=None, disk_used=0, disk_total=0,
                              uptime='', sensors=[], gpu={}, profile=None, profiles=[])
                for timestamp, first, second in ((100.0, 500, 1400), (102.0, 900, 1300)):
                    with patch('anvil.app.channels', return_value=[channel(1, first), channel(2, second)]):
                        window.update_data(dict(sample, time=timestamp))
                self.assertIn('Son 60 sn', window.fan_trend_info.text())
                with patch.object(window, 'refresh'):
                    window.toggle_pause()
                    self.assertIn('güncel değil', window.fan_trend_info.text())
                    self.assertIn('son okumadır', window.fan_status.text())
                    self.assertNotIn('Son 60 sn', window.fan_trend_info.text())
                    self.assertIn('son okuma', window.fan_channel.itemText(0))
                    self.assertIn('güncel olmayabilir', window.fan_curve_info.text())
                    window.fan_channel.setCurrentIndex(1)
                    self.assertIn('duraklatıldı', window.fan_trend_info.text())
                    window.on_error('örnek hata')
                    self.assertIn('DURAKLATILDI', window.status.text())
                    window.toggle_pause()
                    self.assertIn('YENİ ÖLÇÜM BEKLENİYOR', window.status.text())
                    self.assertIn('Yeni ölçüm bekleniyor', window.fan_trend_info.text())
                with patch('anvil.app.channels', return_value=[channel(1, 950), channel(2, 1350)]):
                    window.update_data(dict(sample, time=104.0))
                self.assertIn('1 ölçüm · 1350 RPM', window.fan_trend_info.text())
                self.assertNotIn('son okuma', window.fan_channel.itemText(1))
                self.assertNotIn('güncel olmayabilir', window.fan_curve_info.text())
                window.on_error('örnek hata')
                self.assertIn('Ölçüm yenilenemedi', window.fan_trend_info.text())
                self.assertIn('son okumadır', window.fan_status.text())
                self.assertIn('son okuma', window.fan_channel.itemText(1))
                window.fan_channel.setCurrentIndex(0)
                self.assertIn('Ölçüm yenilenemedi', window.fan_trend_info.text())
                with patch('anvil.app.channels', return_value=[channel(1, 1000), channel(2, 1200)]):
                    window.update_data(dict(sample, time=106.0))
                self.assertIn('1 ölçüm · 1000 RPM', window.fan_trend_info.text())
            finally:
                window.quit_app()

    def test_general_fan_readings_mark_stale_samples_until_new_measurement(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                sample = dict(time=100.0, cpu_usage=None, cpu_temp=None, cpu_mhz=None,
                              memory_used=None, memory_total=None, disk_used=0, disk_total=0,
                              uptime='', sensors=[dict(chip='nct6798', label='CPU Fan',
                                                       value=1500, unit='RPM', path='/mock/fan1_input')],
                              gpu={}, profile=None, profiles=[])
                with patch('anvil.app.channels', return_value=[]):
                    window.update_data(sample)
                self.assertIn('1500 RPM', window.fan_readings.text())
                self.assertFalse(window.fan_readings.text().startswith('Son okuma · '))

                with patch.object(window, 'refresh'):
                    window.toggle_pause()
                    self.assertIn('1500 RPM', window.fan_readings.text())
                    self.assertTrue(window.fan_readings.text().startswith('Son okuma · '))
                    window.toggle_pause()
                    self.assertTrue(window.fan_readings.text().startswith('Son okuma · '))
                    self.assertEqual(window.fan_readings.text().count('Son okuma · '), 1)

                with patch('anvil.app.channels', return_value=[]):
                    window.update_data(dict(sample, time=102.0,
                                            sensors=[dict(chip='nct6798', label='CPU Fan',
                                                          value=1200, unit='RPM', path='/mock/fan1_input')]))
                self.assertIn('1200 RPM', window.fan_readings.text())
                self.assertFalse(window.fan_readings.text().startswith('Son okuma · '))

                window.on_error('örnek hata')
                self.assertIn('1200 RPM', window.fan_readings.text())
                self.assertTrue(window.fan_readings.text().startswith('Son okuma · '))

                with patch('anvil.app.channels', return_value=[]):
                    window.update_data(dict(sample, time=104.0,
                                            sensors=[dict(chip='nct6798', label='CPU Fan',
                                                          value=1250, unit='RPM', path='/mock/fan1_input')]))
                self.assertIn('1250 RPM', window.fan_readings.text())
                self.assertFalse(window.fan_readings.text().startswith('Son okuma · '))
            finally:
                window.quit_app()

    def test_zero_rpm_sensor_readings_do_not_claim_every_fan_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                sample = dict(time=100.0, cpu_usage=None, cpu_temp=None, cpu_mhz=None,
                              memory_used=None, memory_total=None, disk_used=0, disk_total=0,
                              uptime='', sensors=[
                                  dict(chip='generic', label='Fan A', value=0, unit='RPM',
                                       path='/mock/fan1_input'),
                                  dict(chip='generic', label='Fan B', value=0, unit='RPM',
                                       path='/mock/fan2_input')],
                              gpu={}, profile=None, profiles=[])
                with patch('anvil.app.channels', return_value=[]):
                    window.update_data(sample)
                readings = window.fan_readings.text()
                self.assertEqual(readings, 'Fan devir sensörlerinden pozitif RPM okunmadı.')
                self.assertNotIn('tüm fanlar durdu', readings.lower())
                self.assertNotIn('bütün fanlar durdu', readings.lower())
                self.assertIn('0 pozitif RPM okuması / 2 devir sensörü', window.fan_status.text())
                self.assertNotIn('dönen fan', window.fan_status.text().lower())
            finally:
                window.quit_app()

    def test_async_feedback_keeps_original_channel_after_selection_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                window.fan_channel.clear()
                window.fan_channel.addItem('Kanal 1', 1)
                window.fan_channel.addItem('Kanal 2', 2)
                pending = {}
                def capture(program, arguments, callback):
                    pending.update(program=program, arguments=arguments, callback=callback)
                with (patch('anvil.app.channels', return_value=[channel(1, 500), channel(2, 1400)]),
                      patch('anvil.app.Path.exists', return_value=True),
                      patch.object(window, 'run_hardware', side_effect=capture),
                      patch.object(window, 'log_event')):
                    window.fan_action('full')
                    self.assertEqual(pending['arguments'][1:3], ['1', 'full'])
                    self.assertIn('Kanal 1:', window.fan_feedback.text())
                    window.fan_channel.setCurrentIndex(1)
                    verified = {'pwm1_enable': 0}
                    for i in range(1, 6):
                        verified[f'pwm1_auto_point{i}_temp'] = i*10000
                        verified[f'pwm1_auto_point{i}_pwm'] = i*40
                    pending['callback'](True, json.dumps({'ok': True, 'channel': 1,
                                                          'action': 'full', 'verified': verified}), '')
                self.assertIn('Kanal 1:', window.fan_feedback.text())
                self.assertNotIn('Kanal 2:', window.fan_feedback.text())
                self.assertIn('geri okunarak doğrulandı', window.fan_feedback.text())
            finally:
                window.quit_app()

    def test_curve_editor_refuses_a_changed_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                window.fan_channel.clear()
                window.fan_channel.addItem('Kanal 1', 1)
                window.fan_channel.addItem('Kanal 2', 2)
                def change_then_accept(dialog):
                    self.assertIn('Kanal 1', dialog.windowTitle())
                    window.fan_channel.setCurrentIndex(1)
                    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
                    self.assertTrue(any('Fan kanalı değişti' in widget.text()
                                        for widget in dialog.findChildren(QLabel)))
                with (patch('anvil.app.QDialog.exec', new=change_then_accept),
                      patch.object(window, 'fan_action') as action):
                    window.edit_curve()
                    action.assert_not_called()
                with (patch('anvil.app.channels') as scan,
                      patch.object(window, 'run_hardware') as run):
                    window.fan_action('curve', [[30, 50], [45, 55], [60, 70], [75, 100], [85, 100]],
                                      expected_channel=1)
                    scan.assert_not_called()
                    run.assert_not_called()
                self.assertIn('işlem iptal edildi', window.fan_feedback.text())

                window.fan_channel.setCurrentIndex(0)
                def accept_unchanged(dialog):
                    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
                with (patch('anvil.app.QDialog.exec', new=accept_unchanged),
                      patch.object(window, 'fan_action') as action):
                    window.edit_curve()
                    self.assertEqual(action.call_args.kwargs['expected_channel'], 1)
            finally:
                window.quit_app()


if __name__ == '__main__':
    unittest.main()
