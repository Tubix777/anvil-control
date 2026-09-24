"""Read-only fan display tests; no privileged helper or hardware writes."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

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
                with patch('anvil.app.channels', return_value=items):
                    window.update_data(sample)
                self.assertEqual(window.fan_channel.currentData(), 2)
                self.assertEqual(window.fan_channel.itemText(0), 'Kanal 1 · 0 RPM')
                self.assertEqual(window.fan_channel.itemText(1), 'Kanal 2 · 1400 RPM')
                self.assertIn('20 °C → ≈%30', window.fan_curve_info.text())
                window.fan_channel.setCurrentIndex(0)
                self.assertIn('20 °C → ≈%20', window.fan_curve_info.text())
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


if __name__ == '__main__':
    unittest.main()
