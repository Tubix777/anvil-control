"""Headless integration check against real read-only telemetry; no profile changes."""
import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from anvil.app import Window, configure_style

app = QApplication([])
configure_style(app)
w = Window()
w.show()
errors = []


def check():
    try:
        assert w.latest, 'No live sample received'
        assert w.latest['cpu_temp'] is not None
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
        assert w.fan_status.isVisible(), 'Fan panel must be on home page'
        assert 'GPU FAN' in w.gpu_fan.text()
        w.grab().save(str(Path(__file__).resolve().parents[2] / 'anvil-preview.png'))
        print('PASS: live telemetry, seven pages, JSON/CSV exports, screenshot')
    except Exception as e:
        errors.append(e)
    finally:
        w.quit_app()
        app.quit()


QTimer.singleShot(4500, check)
app.exec()
if errors:
    raise errors[0]
