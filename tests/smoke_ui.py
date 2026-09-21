"""Headless integration check against real read-only telemetry; no profile changes."""
import csv
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QTimer, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from anvil.app import Window, configure_style

app = QApplication([])
configure_style(app)
test_config = tempfile.TemporaryDirectory()
with patch('anvil.app.QSettings', return_value=QSettings(str(Path(test_config.name)/'settings.ini'), QSettings.Format.IniFormat)):
    w = Window()
w.show()
errors = []


def check():
    try:
        assert w.latest, 'No live sample received'
        assert w.latest['cpu_temp'] is not None
        if Path('/usr/libexec/anvil-fan-helper').exists():
            assert all(b.isEnabled() for b in w.fan_controls)
        if shutil.which('openrgb'):
            w.scan_rgb()
            for _ in range(310):
                if not w.hardware_busy():
                    break
                QTest.qWait(100)
            assert not w.hardware_busy(), 'RGB scan did not finish'
            if w.rgb_devices.count():
                assert w.rgb_modes.count() > 0
                assert w.rgb_apply.isEnabled()
        w.sensor_search.setText('coretemp')
        assert w.sensor_table.rowCount() > 0
        assert all(w.sensor_table.item(i, 0).text() == 'coretemp' for i in range(w.sensor_table.rowCount()))
        w.sensor_search.setText('no-such-sensor')
        assert w.sensor_table.rowCount() == 0
        w.sensor_search.clear()
        w.reset_stats()
        assert all(low == high for low, high in w.stats.values.values())
        w.chart_choice.setCurrentIndex(1)
        assert w.chart.caption == 'GPU %'
        w.chart_choice.setCurrentIndex(0)
        before = len(w.history)
        w.toggle_pause()
        w.update_data(w.latest)
        assert len(w.history) == before
        assert not w.rotor.timer.isActive()
        w.toggle_pause()
        for n in range(7):
            w.navigate(n)
            app.processEvents()
            assert w.stack.currentIndex() == n
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'report.json'
            metrics = Path(directory) / 'metrics.csv'
            with patch('anvil.app.QFileDialog.getSaveFileName', return_value=(str(report), '')):
                w.export_json()
            assert json.loads(report.read_text())['hardware']['board'] == 'PRIME H610M-K D4'
            with patch('anvil.app.QFileDialog.getSaveFileName', return_value=(str(metrics), '')):
                w.export_csv()
            with metrics.open() as stream:
                assert len(list(csv.reader(stream))) > 1
        w.navigate(0)
        app.processEvents()
        w.rotor.set_speed(30)
        assert w.rotor.timer.isActive()
        QTest.qWait(100)
        assert w.rotor.angle > 0
        w.set_motion(False)
        assert not w.rotor.timer.isActive()
        assert w.fade_effect.opacity() == 1
        w.set_motion(True)
        w.rotor.set_speed((w.latest['gpu'] or {}).get('fan'))
        QTest.qWait(900)
        assert w.fan_status.isVisible(), 'Fan panel must be on home page'
        assert 'GPU FAN' in w.gpu_fan.text()
        w.grab().save(str(Path(__file__).resolve().parents[2] / 'anvil-preview.png'))
        print('PASS: telemetry, seven pages, search, extrema reset, chart selection, pause, animations, JSON/CSV and screenshot')
    except Exception as e:
        errors.append(e)
    finally:
        w.quit_app()
        app.quit()


QTimer.singleShot(4500, check)
app.exec()
if errors:
    raise errors[0]
test_config.cleanup()
