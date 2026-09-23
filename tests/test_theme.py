import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from anvil.app import (DEFAULT_THEME, STYLE, STYLE_COLOR_ROLES, THEMES, Window,
                       configure_style, resolve_theme, style_for_theme)


class ThemeTests(unittest.TestCase):
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
                self.assertEqual(first.board.theme, THEMES['night'])
                self.assertEqual(first.chart.theme, THEMES['night'])
                self.assertEqual(first.rotor.accent_color, THEMES['night']['accent'])
                self.assertTrue(all(m.accent_color == THEMES['night']['accent']
                                    for m in first.meters.values()))
                self.assertEqual(app.styleSheet(), style_for_theme('night'))
            finally:
                first.quit_app()
            with patch('anvil.app.QSettings', return_value=settings):
                reopened = Window()
            try:
                self.assertEqual(reopened.theme_key, 'night')
                self.assertEqual(reopened.theme_combo.currentData(), 'night')
                self.assertEqual(app.styleSheet(), style_for_theme('night'))
            finally:
                reopened.quit_app()
