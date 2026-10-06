"""Exercise installed monitoring packages on Linux without assuming test hardware.

Run with the package's Python interpreter. Real /proc and available sysfs are
read, but no fan, RGB or power operations are sent to the system.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['ANVIL_MONITOR_ONLY'] = '1'

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from anvil.app import Window, configure_style


def check_package():
    app = QApplication.instance() or QApplication([])
    configure_style(app)
    callback_errors = []
    with (tempfile.TemporaryDirectory() as directory,
          patch.object(sys, 'excepthook',
                       lambda _kind, error, _traceback: callback_errors.append(error))):
        settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
        with patch('anvil.app.QSettings', return_value=settings):
            window = Window()
        window.show()
        try:
            for _ in range(100):
                QTest.qWait(100)
                if window.latest is not None:
                    break
            assert not callback_errors, f'Qt callback failed: {callback_errors!r}'
            assert window.latest is not None, 'Installed package failed to sample'
            assert window.monitor_only, 'Package must start in monitoring mode'
            assert all(not control.isEnabled() for control in window.fan_controls)
            assert all(not control.isEnabled() for control in window.profile_buttons.values())
            assert not window.rgb_apply.isEnabled()
            assert len(window.nav) == 5
            for index in range(len(window.nav)):
                window.navigate(index)
                app.processEvents()
                assert window.stack.currentIndex() == index
            theme_index = window.quick_theme.currentIndex()
            window.quick_theme.setCurrentIndex((theme_index + 1) % window.quick_theme.count())
            app.processEvents()
            assert window.theme_combo.currentData() == window.quick_theme.currentData()
            window.sensor_search.setText('anvil-nonexistent-driver')
            assert window.sensor_table.rowCount() == 0
            window.sensor_search.clear()
            with (patch.object(window, 'run_hardware') as hardware,
                  patch('anvil.app.ProfileWorker') as power,
                  patch('anvil.app.QProcess.startDetached') as external):
                window.fan_action('full')
                window.apply_profile('balanced')
                window.apply_rgb()
                window.open_rgb()
                hardware.assert_not_called()
                power.assert_not_called()
                external.assert_not_called()
            assert not callback_errors, f'Qt callback failed: {callback_errors!r}'
            print('PASS: installed package, live read-only sample, five pages, themes, filters and write guards')
        finally:
            window.quit_app()
            app.processEvents()


if __name__ == '__main__':
    check_package()
