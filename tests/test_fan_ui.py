"""Read-only fan display tests; no privileged helper or hardware writes."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QLabel

from anvil.app import (Window, configure_style, fan_channel_label,
                       hardware_fan_curve_text, preferred_fan_channel)


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
        self.assertIn('70 °C → ≈%100', current)
        self.assertIn('PECI Agent 0 31 °C', current)
        self.assertIn('hızlanma 0 ms / yavaşlama 0 ms', current)
        self.assertIn('gecikme yok', current)
        inactive = hardware_fan_curve_text(channel(2, 1400, mode='0'))
        self.assertIn('şu an tam hız etkin', inactive)
        self.assertNotIn('etkin otomatik eğri', inactive)
        broken = channel(2, 1400, points=[[20, None]])
        self.assertIn('beş noktanın tamamı okunamadı', hardware_fan_curve_text(broken))
        self.assertIn('yalnızca önizlemedir', hardware_fan_curve_text(None))

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
