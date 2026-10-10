"""Synthetic animation preview: no host telemetry and no hardware operations."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

os.environ['ANVIL_MONITOR_ONLY'] = '1'
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from anvil.app import Window, configure_style


def render(destination):
    app = QApplication.instance() or QApplication([])
    configure_style(app)
    identity = dict(board='ASUS · Örnek sistem', vendor='ASUSTeK COMPUTER INC.',
                    asus=True, openrgb=None, os='Linux · önizleme', kernel='—',
                    cpu='Örnek işlemci', gpu='Örnek ekran kartı', bios='—',
                    bios_date='—', pci='', pwm=[], capabilities={})
    sample = dict(time=1., cpu_usage=28, cpu_temp=43, cpu_mhz=3200,
                  memory_used=6 * 1024**3, memory_total=16 * 1024**3,
                  disk_used=110 * 1024**3, disk_total=512 * 1024**3,
                  uptime=7200, sensors=[], profiles=[],
                  gpu=dict(usage=18, temperature=38, fan=30), profile=None)
    frames = []
    with tempfile.TemporaryDirectory() as directory:
        settings = QSettings(str(Path(directory) / 'preview.ini'), QSettings.Format.IniFormat)
        with (patch('anvil.app.QSettings', return_value=settings),
              patch('anvil.app.Monitor', return_value=SimpleNamespace(identity=identity)),
              patch.object(Window, 'refresh'), patch('anvil.app.channels', return_value=[]),
              patch('anvil.app.Path.glob', return_value=[])):
            window = Window()
            window.resize(1120, 880)
            window.update_data(sample)
            window.show()
            window.status.setText('● GÖRSEL ÖNİZLEME · SİMÜLASYON — donanım işlemi yapılmaz')
            try:
                QTest.qWait(750)
                window.grab().save(str(destination / 'anvil-motion.png'))
                window.navigate(1)
                for frame in range(120):
                    if frame == 26:
                        window.navigate(0)
                    if frame == 53:
                        window.nav[0]._hover_to(1)
                        window.nav[0]._press()
                    if frame == 75:
                        window.apply_theme('night')
                    if frame == 99:
                        window.apply_theme('anvil')
                    QTest.qWait(40)
                    qimage = window.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
                    image = Image.frombytes('RGBA', (qimage.width(), qimage.height()),
                                            bytes(qimage.bits()), 'raw', 'RGBA', qimage.bytesPerLine())
                    frames.append(image.resize((840, 660)).convert('RGB'))
                frames[0].save(destination / 'anvil-motion.gif', save_all=True,
                               append_images=frames[1:], duration=40, loop=0)
            finally:
                window.quit_app()


if __name__ == '__main__':
    import sys
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    render(destination)
