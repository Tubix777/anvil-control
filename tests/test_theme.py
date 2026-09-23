import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from anvil.app import (DEFAULT_THEME, STYLE, STYLE_COLOR_ROLES, THEMES, THEME_NAMES,
                       Window, configure_style, resolve_theme, style_for_theme)


class ThemeTests(unittest.TestCase):
    def test_seven_themes_have_readable_primary_text(self):
        self.assertEqual(set(THEMES), set(THEME_NAMES))
        self.assertEqual(len(THEMES), 7)
        def luminance(color):
            parts = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
            linear = [v/12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4 for v in parts]
            return sum(weight*value for weight, value in zip((0.2126, 0.7152, 0.0722), linear))
        def contrast(left, right):
            a, b = luminance(left), luminance(right)
            return (max(a, b)+0.05)/(min(a, b)+0.05)
        for name, theme in THEMES.items():
            with self.subTest(theme=name):
                for front, back in [('foreground', 'background'), ('muted', 'background'),
                                    ('on_accent', 'accent')]:
                    self.assertGreaterEqual(contrast(theme[front], theme[back]), 4.5)

    def test_every_stylesheet_color_has_a_palette_role(self):
        colors = {value.lower() for value in re.findall(r'#[0-9a-fA-F]{6}', STYLE)}
        self.assertEqual(colors, set(STYLE_COLOR_ROLES))
        self.assertEqual(style_for_theme(DEFAULT_THEME), STYLE)
        for key, palette in THEMES.items():
            with self.subTest(theme=key):
                self.assertTrue(set(STYLE_COLOR_ROLES.values()) <= set(palette))
                self.assertIn(palette['accent'], style_for_theme(key))
                self.assertIn(palette['background'], style_for_theme(key))
        self.assertEqual(resolve_theme('unsupported'), DEFAULT_THEME)

    def test_theme_selection_persists_and_updates_custom_widgets(self):
        app = QApplication.instance() or QApplication([])
        configure_style(app)
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings):
                first = Window()
            try:
                index = first.theme_combo.findData('night')
                self.assertGreaterEqual(index, 0)
                first.theme_combo.setCurrentIndex(index)
                self.assertEqual(settings.value('theme'), 'night')
                self.assertEqual(first.quick_theme.currentData(), 'night')
                self.assertEqual(first.board.theme, THEMES['night'])
                self.assertEqual(first.chart.theme, THEMES['night'])
                self.assertEqual(first.rotor.accent_color, THEMES['night']['accent'])
                self.assertTrue(all(m.accent_color == THEMES['night']['accent']
                                    for m in first.meters.values()))
                self.assertEqual(app.styleSheet(), style_for_theme('night'))
                first.quick_theme.setCurrentIndex(first.quick_theme.findData('daylight'))
                self.assertEqual(first.theme_combo.currentData(), 'daylight')
                self.assertEqual(settings.value('theme'), 'daylight')
                first.theme_combo.setCurrentIndex(index)
            finally:
                first.quit_app()
            with patch('anvil.app.QSettings', return_value=settings):
                reopened = Window()
            try:
                self.assertEqual(reopened.theme_key, 'night')
                self.assertEqual(reopened.theme_combo.currentData(), 'night')
                self.assertEqual(reopened.quick_theme.currentData(), 'night')
                self.assertEqual(app.styleSheet(), style_for_theme('night'))
            finally:
                reopened.quit_app()

    def test_missing_metrics_and_unverified_asus_board_remain_read_only(self):
        app = QApplication.instance() or QApplication([])
        configure_style(app)
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings):
                window = Window()
            try:
                window.monitor.identity.update(board='ROG STRIX X670E-E GAMING WIFI',
                                               vendor='ASUSTeK COMPUTER INC.', asus=True)
                sample = dict(time=0, cpu_usage=None, cpu_temp=None, cpu_mhz=None,
                              memory_used=None, memory_total=None, disk_used=0, disk_total=0,
                              uptime='', sensors=[], gpu={'name':'GPU without VRAM telemetry',
                              'memory_total':1024}, profile=None, profiles=[])
                with patch('anvil.app.channels', return_value=[]):
                    window.update_data(sample)
                window.chart_choice.setCurrentIndex(4)
                self.assertEqual(window.cards['ram'].text(), '—')
                self.assertIn('Fan yazma: kapalı', window.compatibility.text())
                self.assertFalse(window.preset_apply.isEnabled())
                self.assertTrue(window.preset_combo.isEnabled())
                self.assertIn('henüz doğrulanmadı', window.fan_feedback.text())
            finally:
                window.quit_app()
