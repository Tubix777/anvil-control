import csv
import json
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings, QProcess, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QFileDialog, QMessageBox, QComboBox, QSystemTrayIcon, QMenu,
    QCheckBox, QScrollArea)
from .backend import Monitor, set_profile

STYLE = '''
QWidget { background:#101010; color:#f2f1ec; font-size:13px; }
QLabel { background:transparent; }
QMainWindow { background:#101010; }
QFrame#sidebar { background:#090909; border-right:1px solid #2d2b23; }
QFrame#card { background:#191917; border:1px solid #35332b; border-radius:14px; }
QFrame#card QLabel { background:transparent; }
QLabel#title { font-size:29px; font-weight:700; }
QLabel#brand { color:#ffd438; font-size:27px; font-weight:800; letter-spacing:3px; }
QLabel#muted { color:#b3b0a3; }
QLabel#value { font-size:29px; font-weight:600; }
QLabel#section { font-size:18px; font-weight:600; }
QLabel#accent { color:#ffd438; font-weight:600; }
QPushButton { background:#25241e; border:1px solid #484332; border-radius:8px; padding:11px 17px; }
QPushButton:hover { background:#3b3520; border-color:#ffd438; }
QPushButton:checked { background:#ffd438; color:#111111; border-color:#ffd438; }
QPushButton:disabled { color:#817e71; background:#1c1c19; border-color:#35332b; }
QPushButton#nav { text-align:left; border:0; padding:14px; background:transparent; }
QPushButton#nav:checked { background:#ffd438; color:#111111; font-weight:600; }
QTableWidget { background:#171715; border:1px solid #35332b; border-radius:9px; gridline-color:#302e27; }
QHeaderView::section { background:#26251f; color:#ccc7b4; border:0; padding:11px; }
QTableWidget::item { padding:8px; }
QTextEdit { background:#171715; border:1px solid #35332b; border-radius:10px; padding:12px; }
QComboBox { background:#25241e; padding:9px; border:1px solid #484332; border-radius:6px; }
QScrollArea { border:0; }
QToolTip { background:#25241e; color:#f2f1ec; border:1px solid #ffd438; }
'''


def configure_style(app):
    family = next((name for name in ['Adwaita Sans', 'Noto Sans', 'DejaVu Sans']
                   if name in QFontDatabase.families()), 'Sans Serif')
    font = QFont(family, 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)


class Motherboard(QWidget):
    """Original component diagram, not an electrical or pinout reference."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 230)
        self.setAccessibleName('Anakartın temsili bileşen şeması')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = min(self.width()/350, self.height()/250)
        p.translate((self.width()-350*scale)/2, (self.height()-250*scale)/2)
        p.scale(scale, scale)
        p.setBrush(QColor('#11120f'))
        p.setPen(QPen(QColor('#807038'), 1.5))
        p.drawRoundedRect(QRectF(51, 9, 248, 229), 8, 8)
        p.setPen(QPen(QColor('#383722'), 1))
        for i in range(7):
            p.drawPolyline([QPointF(x, y)
                            for x, y in [(130+i*6, 115), (130+i*6, 143+i*3), (217, 143+i*3)]])
        def block(x, y, w, h, title='', accent=False):
            p.setBrush(QColor('#35301c' if accent else '#242520'))
            p.setPen(QPen(QColor('#e0bb36' if accent else '#64644f'), 1))
            p.drawRoundedRect(QRectF(x, y, w, h), 2, 2)
            if title:
                f = QFont(self.font())
                f.setPixelSize(9)
                f.setWeight(QFont.Weight.DemiBold)
                p.setFont(f)
                p.setPen(QColor('#ffe178' if accent else '#c3c3af'))
                p.drawText(QRectF(x, y, w, h), Qt.AlignmentFlag.AlignCenter, title)
        block(116, 43, 87, 80, 'LGA 1700\nCPU', True)
        for x in [225, 244]:
            block(x, 32, 11, 110, '', True)
        block(278, 48, 10, 72)
        for y in [29, 62, 96]:
            block(43, y, 32, 25, 'I/O')
        for x in range(90, 207, 17):
            block(x, 22, 11, 10)
        for y in range(49, 121, 18):
            block(89, y, 13, 12)
        block(94, 150, 114, 10, 'M.2')
        block(81, 174, 158, 14, 'PCIe 4.0 ×16', True)
        block(81, 205, 66, 11, 'PCIe ×1')
        block(223, 198, 38, 26, 'H610')
        block(274, 175, 20, 44, 'S')
        for x, y in [(62, 19), (288, 19), (62, 227), (288, 227)]:
            p.setPen(QPen(QColor('#82794d'), 2))
            p.setBrush(QColor('#101010'))
            p.drawEllipse(QRectF(x-3, y-3, 6, 6))
        p.end()


def label(text, kind=None):
    w = QLabel(text)
    w.setWordWrap(True)
    if kind:
        w.setObjectName(kind)
    return w


def button(text, action):
    b = QPushButton(text)
    b.clicked.connect(action)
    return b


def table(headers):
    w = QTableWidget(0, len(headers))
    w.setHorizontalHeaderLabels(headers)
    w.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    w.verticalHeader().hide()
    w.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    w.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    return w


def rows(widget, data):
    widget.setRowCount(len(data))
    for i, row in enumerate(data):
        for j, value in enumerate(row):
            widget.setItem(i, j, QTableWidgetItem(str(value)))


def fmt(v, unit='', digits=0):
    return '—' if v is None else f'{v:.{digits}f}{unit}'


class Chart(QWidget):
    def __init__(self):
        super().__init__()
        self.values = deque(maxlen=120)
        self.setMinimumHeight(100)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = self.rect().adjusted(40, 16, -12, -28)
        p.setPen(QColor('#35332b'))
        for n in range(5):
            y = bounds.bottom() - n * bounds.height()/4
            p.setPen(QColor('#35332b'))
            p.drawLine(bounds.left(), int(y), bounds.right(), int(y))
            p.setPen(QColor('#b3b0a3'))
            p.drawText(0, int(y)+4, str(n*25))
        p.setPen(QColor('#b3b0a3'))
        p.drawText(40, self.height()-4, 'CPU %   •   Son 120 ölçüm')
        if len(self.values) > 1:
            path = QPainterPath()
            for i, value in enumerate(self.values):
                x = bounds.left() + i*bounds.width()/119
                y = bounds.bottom() - value*bounds.height()/100
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            p.setPen(QPen(QColor('#ffd438'), 2.5))
            p.drawPath(path)
        p.end()


class Worker(QThread):
    result = Signal(dict)
    error = Signal(str)

    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor

    def run(self):
        try:
            self.result.emit(self.monitor.sample())
        except Exception as e:
            self.error.emit(str(e))


class ProfileWorker(QThread):
    result = Signal(bool, str)

    def __init__(self, profile):
        super().__init__()
        self.profile = profile

    def run(self):
        self.result.emit(*set_profile(self.profile))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Anvil Control • ASUS masaüstü kontrol merkezi')
        self.resize(1280, 920)
        self.setMinimumSize(940, 680)
        self.settings = QSettings('Anvil', 'AnvilControl')
        self.monitor = Monitor()
        self.latest = None
        self.history = deque(maxlen=3600)
        self.profile_job = None
        self.profile_pending = False
        self.worker = Worker(self.monitor)
        self.worker.result.connect(self.update_data)
        self.worker.error.connect(self.on_error)
        root = QWidget()
        self.setCentralWidget(root)
        horizontal = QHBoxLayout(root)
        horizontal.setContentsMargins(0, 0, 0, 0)
        side = QFrame()
        side.setObjectName('sidebar')
        side.setFixedWidth(228)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(18, 28, 18, 20)
        sl.addWidget(label('ANVIL', 'brand'))
        sl.addWidget(label('CONTROL CENTER\n0.2 ALPHA', 'muted'))
        sl.addSpacing(30)
        self.stack = QStackedWidget()
        self.nav = []
        names = ['Genel bakış', 'Sensörler', 'Güç profilleri', 'Aydınlatma', 'Donanım', 'Tanılama', 'Ayarlar']
        for i, name in enumerate(names):
            b = QPushButton(f'{i+1:02}   {name}')
            b.setObjectName('nav')
            b.setCheckable(True)
            b.clicked.connect(lambda checked=False, n=i: self.navigate(n))
            self.nav.append(b)
            sl.addWidget(b)
        sl.addStretch()
        sl.addWidget(label(self.monitor.identity['board'], 'section'))
        sl.addWidget(label('Yerel veriler · Bulut bağlantısı yok', 'muted'))
        horizontal.addWidget(side)
        horizontal.addWidget(self.stack, 1)
        self.build_overview()
        self.build_thermal()
        self.build_profiles()
        self.build_rgb()
        self.build_hardware()
        self.build_diagnostics()
        self.build_settings()
        self.navigate(0)
        self.tray = QSystemTrayIcon(QIcon.fromTheme('computer'), self)
        self.tray.setToolTip('Anvil Control')
        menu = QMenu()
        menu.addAction('Anvil’i göster', self.showNormal)
        menu.addAction('Çıkış', self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(self.settings.value('interval', 2, type=int)*1000)
        self.refresh()

    def page(self, title, subtitle):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 28, 30, 24)
        layout.setSpacing(18)
        layout.addWidget(label(title, 'title'))
        layout.addWidget(label(subtitle, 'muted'))
        scroll.setWidget(page)
        self.stack.addWidget(scroll)
        return layout

    def card(self, heading, detail):
        frame = QFrame()
        frame.setObjectName('card')
        v = QVBoxLayout(frame)
        v.setContentsMargins(20, 18, 20, 18)
        v.addWidget(label(heading, 'muted'))
        val = label(detail, 'value')
        v.addWidget(val)
        return frame, val

    def build_overview(self):
        l = self.page('Kontrol sende.', 'Donanımın, sıcaklıkların ve fanların tek ekranda.')
        self.status = label('Sensörler okunuyor…', 'muted')
        l.addWidget(self.status)
        top = QHBoxLayout()
        board = QFrame()
        board.setObjectName('card')
        bv = QVBoxLayout(board)
        bv.setContentsMargins(14, 10, 14, 14)
        bv.addWidget(Motherboard())
        name = label(self.monitor.identity['board'], 'section')
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bv.addWidget(name)
        note = label('ASUS  /  Temsili bileşen şeması', 'muted')
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bv.addWidget(note)
        top.addWidget(board, 1)
        grid = QGridLayout()
        self.cards = {}
        for i, (key, text) in enumerate([('cpu', 'İŞLEMCİ SICAKLIĞI'), ('load', 'CPU KULLANIMI'),
                                       ('gpu', 'GPU SICAKLIĞI'), ('ram', 'BELLEK KULLANIMI')]):
            frame, value = self.card(text, '—')
            grid.addWidget(frame, i//2, i%2)
            self.cards[key] = value
        top.addLayout(grid, 1)
        l.addLayout(top)
        fan_card = QFrame()
        fan_card.setObjectName('card')
        fv = QVBoxLayout(fan_card)
        fv.setContentsMargins(20, 14, 20, 14)
        fh = QHBoxLayout()
        fh.addWidget(label('Fan merkezi', 'section'))
        fh.addStretch()
        self.gpu_fan = label('GPU FAN  —', 'accent')
        fh.addWidget(self.gpu_fan)
        fv.addLayout(fh)
        self.fan_status = label('Fan arayüzleri taranıyor…')
        fv.addWidget(self.fan_status)
        self.fan_readings = label('', 'accent')
        fv.addWidget(self.fan_readings)
        fv.addWidget(label('Fan eğrisi desteği henüz yok. Anakart fanlarını UEFI Q-Fan üzerinden ayarlayabilirsiniz.', 'muted'))
        l.addWidget(fan_card)
        self.chart = Chart()
        l.addWidget(self.chart)
        self.summary = label('Veriler bekleniyor…', 'muted')
        l.addWidget(self.summary)
        bar = QHBoxLayout()
        bar.addWidget(button('Sensörleri incele', lambda: self.navigate(1)))
        bar.addWidget(button('CSV kaydını dışa aktar', self.export_csv))
        bar.addStretch()
        l.addLayout(bar)
        l.addStretch()

    def build_thermal(self):
        l = self.page('Sensörler', 'Tüm sıcaklık ve devir okumaları • Fan özeti ana sayfada')
        self.sensor_table = table(['Kaynak', 'Sensör', 'Değer'])
        self.sensor_table.setMinimumHeight(360)
        l.addWidget(self.sensor_table)
        l.addWidget(label('Fan eğrisi kontrolü: bu alpha sürümünde uygulanmıyor. PWM arayüzü bulunsa bile kanal eşlemesi ve güvenli geri dönüş doğrulanmadan hız değiştirilmez.', 'muted'))
        l.addWidget(label('H610M-K D4 üzerinde fan ayarları için mevcut UEFI Q-Fan ayarlarını kullanabilirsiniz. Uygulama firmware fan yönetimini değiştirmez.', 'muted'))

    def build_profiles(self):
        l = self.page('Güç profilleri', 'Sistemin sunduğu profiller • Değişiklikler tüm sistem için geçerlidir')
        self.active_profile = label('Etkin profil okunuyor…', 'section')
        l.addWidget(self.active_profile)
        self.profile_buttons = {}
        for key, title, detail in [
            ('power-saver', 'Enerji tasarrufu', 'Sistem servisinin enerji tasarrufu politikasını etkinleştirir.'),
            ('balanced', 'Dengeli', 'Sistem servisinin dengeli politikasını etkinleştirir.'),
            ('performance', 'Performans', 'Sistem servisinin performans politikasını etkinleştirir.')]:
            b = button(title, lambda checked=False, p=key: self.apply_profile(p))
            b.setCheckable(True)
            b.setEnabled(False)
            self.profile_buttons[key] = b
            l.addWidget(b)
            l.addWidget(label(detail, 'muted'))
        self.profile_feedback = label('Bu profiller özel fan eğrisi veya GPU hız aşırtması uygulamaz.', 'muted')
        l.addWidget(self.profile_feedback)
        l.addStretch()

    def build_rgb(self):
        l = self.page('Aydınlatma', 'Bağlı donanıma göre RGB desteği')
        l.addWidget(label('Anakart RGB kontrolü doğrulanmadı', 'section'))
        l.addWidget(label('PRIME H610M-K D4 ile H610M-K D4 ARGB farklı modellerdir. RGB bağlantısının bulunması, yazılımdan kontrol edilebildiği anlamına gelmez.'))
        l.addWidget(label('Bu sürüm RGB ayarı uygulamaz. OpenRGB kuruluysa ayrı uygulamayı açabilirsiniz; cihaz uyumluluğu OpenRGB içinde doğrulanmalıdır.', 'muted'))
        b = button('OpenRGB’yi aç', self.open_rgb)
        b.setEnabled(bool(self.monitor.identity['openrgb']))
        l.addWidget(b)
        l.addWidget(label('OpenRGB bulundu.' if self.monitor.identity['openrgb'] else 'OpenRGB bu sistemde kurulu değil.', 'muted'))
        l.addStretch()

    def build_hardware(self):
        l = self.page('Donanım envanteri', 'Seri numarası ve makine kimliği toplanmaz')
        t = table(['Bileşen', 'Bilgi'])
        info = self.monitor.identity
        rows(t, [(title, info[key]) for key, title in [('board', 'Anakart'), ('vendor', 'Üretici'),
            ('cpu', 'İşlemci'), ('os', 'İşletim sistemi'), ('kernel', 'Kernel'), ('bios', 'BIOS sürümü'), ('bios_date', 'BIOS tarihi')]])
        t.setMinimumHeight(300)
        l.addWidget(t)
        l.addWidget(label('PCI aygıtları ve sürücüler', 'section'))
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(info['pci'] or 'lspci kullanılamıyor.')
        text.setMinimumHeight(190)
        l.addWidget(text)

    def build_diagnostics(self):
        l = self.page('Tanılama', 'Eksik desteği görünür kıl • Raporu paylaşmadan önce incele')
        self.diagnostics = QTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setMinimumHeight(350)
        l.addWidget(self.diagnostics)
        bar = QHBoxLayout()
        bar.addWidget(button('Yeniden kontrol et', self.refresh))
        bar.addWidget(button('JSON raporu kaydet', self.export_json))
        l.addLayout(bar)
        l.addWidget(label('Rapor: anakart, BIOS, işletim sistemi, PCI aygıtları, sensörler ve destek durumu. Otomatik gönderim yapılmaz.', 'muted'))

    def build_settings(self):
        l = self.page('Ayarlar', 'Görünürlük ve veri toplama tercihleri')
        l.addWidget(label('Yenileme aralığı', 'section'))
        combo = QComboBox()
        for seconds in [1, 2, 5, 10]:
            combo.addItem(f'{seconds} saniye', seconds)
        combo.setCurrentIndex(max(0, combo.findData(self.settings.value('interval', 2, type=int))))
        combo.currentIndexChanged.connect(lambda: self.interval_changed(combo.currentData()))
        l.addWidget(combo)
        self.close_to_tray = QCheckBox('Pencereyi kapatınca sistem tepsisinde çalışmaya devam et')
        self.close_to_tray.setChecked(self.settings.value('tray', False, type=bool))
        self.close_to_tray.toggled.connect(lambda value: self.settings.setValue('tray', value))
        l.addWidget(self.close_to_tray)
        l.addWidget(label('Grafikte son 120 ölçüm; dışa aktarma için bellekte son 3.600 ölçüm tutulur. Uygulama kapanınca geçmiş silinir. Yalnızca dışa aktardığınız kayıtlar diske yazılır.', 'muted'))
        l.addWidget(label('Anvil Control 0.2.0 • Alpha\nBağımsız, açık kaynaklı bir proje. ASUS tarafından geliştirilmemiştir.\nFan/RGB yazma desteği ve geniş donanım doğrulaması henüz tamamlanmadı.', 'muted'))
        l.addStretch()

    def navigate(self, index):
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav):
            b.setChecked(i == index)

    def interval_changed(self, seconds):
        self.settings.setValue('interval', seconds)
        self.timer.setInterval(seconds*1000)

    def refresh(self):
        if not self.worker.isRunning():
            self.worker.start()

    def on_error(self, error):
        self.status.setText('Ölçüm alınamadı: ' + error + ' • Ekrandaki değerler eski olabilir.')

    def update_data(self, d):
        self.latest = d
        self.history.append(d)
        gpu = d['gpu'] or {}
        self.cards['cpu'].setText(fmt(d['cpu_temp'], ' °C'))
        self.cards['load'].setText(fmt(d['cpu_usage'], ' %'))
        self.cards['gpu'].setText(fmt(gpu.get('temperature'), ' °C'))
        self.cards['ram'].setText(f"{d['memory_used']/2**30:.1f} / {d['memory_total']/2**30:.1f} GB")
        if d['cpu_usage'] is not None:
            self.chart.values.append(d['cpu_usage'])
            self.chart.update()
        stamp = datetime.fromtimestamp(d['time']).strftime('%H:%M:%S')
        self.status.setText(f'●  CANLI   •   Son ölçüm {stamp}   •   {self.monitor.identity["os"]}')
        self.summary.setText(f"{gpu.get('name', 'GPU telemetrisi kullanılamıyor')}\n"
            f"GPU kullanımı {fmt(gpu.get('usage'), ' %')}   ·   Güç {fmt(gpu.get('power'), ' W', 1)}   ·   GPU fanı {fmt(gpu.get('fan'), ' %')}\n"
            f"CPU frekansı {fmt(d['cpu_mhz'], ' MHz')}   ·   Açık kalma {float(d['uptime'])/3600:.1f} saat   ·   Disk / {d['disk_used']/2**30:.0f} / {d['disk_total']/2**30:.0f} GB")
        rows(self.sensor_table, [(s['chip'], s['label'], fmt(s['value'], ' '+s['unit'], 1)) for s in d['sensors']])
        fans = [s for s in d['sensors'] if s['unit'] == 'RPM']
        self.gpu_fan.setText('GPU FAN  ' + fmt(gpu.get('fan'), ' %'))
        self.fan_readings.setText('  ·  '.join(f"{s['chip']} / {s['label']}: {s['value']:.0f} RPM" for s in fans))
        self.fan_readings.setVisible(bool(fans))
        pwm = list(Path('/sys/class/hwmon').glob('hwmon*/pwm[0-9]'))
        self.monitor.identity['pwm'] = [str(p) for p in pwm]
        self.fan_status.setText(f'{len(fans)} fan devir sensörü • {len(pwm)} PWM arayüzü bulundu.' if fans or pwm
                               else 'Fan devir / PWM arayüzü görünmüyor. Mevcut kernel sürücülerinden fan kontrolü alınamıyor.')
        names = {'power-saver':'Enerji tasarrufu', 'balanced':'Dengeli', 'performance':'Performans'}
        self.active_profile.setText('Etkin profil: ' + names.get(d['profile'], d['profile'] or 'Servise erişilemiyor'))
        available = [p.get('Profile', {}).get('data') for p in d['profiles']]
        for key, b in self.profile_buttons.items():
            b.setEnabled(key in available and not self.profile_pending)
            b.setChecked(key == d['profile'])
        self.diagnostics.setPlainText('\n\n'.join([
            'SICAKLIKLAR\n' + f"{len(d['sensors'])} sensör okunuyor.",
            'FAN KONTROLÜ\n' + self.fan_status.text() + '\nBu sürümde fanlara yazma uygulanmaz.',
            'GPU\n' + (gpu.get('name', '') + ' • NVIDIA NVML ile okunuyor.' if gpu else 'NVML telemetrisi alınamadı. Donanım ekranından sürücüyü inceleyin.'),
            'GÜÇ PROFİLLERİ\n' + (', '.join(available) if available else 'Güç profili servisine erişilemiyor.'),
            'RGB\nAnakart kontrolü doğrulanmadı. Donanıma yazma yapılmıyor.',
            'KAPSAM\nBu rapor yalnızca mevcut sistemde görünür arayüzleri gösterir. Bir arayüzün eksik olması donanımın kesinlikle desteklenmediği anlamına gelmez.'
        ]))

    def apply_profile(self, profile):
        if self.profile_pending:
            return
        self.profile_pending = True
        for b in self.profile_buttons.values():
            b.setEnabled(False)
        self.profile_feedback.setText('Sistem profili uygulanıyor… Gerekirse masaüstü kimlik doğrulamasını tamamlayın.')
        self.profile_job = ProfileWorker(profile)
        self.profile_job.result.connect(self.profile_done)
        self.profile_job.start()

    def profile_done(self, success, message):
        self.profile_pending = False
        self.profile_feedback.setText(('✓ ' if success else 'Değişiklik başarısız: ') + message)
        self.refresh()

    def open_rgb(self):
        path = self.monitor.identity['openrgb']
        if path:
            success, _ = QProcess.startDetached(path, [])
            if not success:
                QMessageBox.warning(self, 'OpenRGB', 'Uygulama başlatılamadı.')

    def export_json(self):
        if not self.latest:
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'Tanılama raporu', 'anvil-report.json', 'JSON (*.json)')
        if filename:
            try:
                Path(filename).write_text(json.dumps({'version':'0.2.0', 'hardware':self.monitor.identity,
                    'snapshot':self.latest}, indent=2, ensure_ascii=False))
            except OSError as e:
                QMessageBox.warning(self, 'Kaydedilemedi', str(e))

    def export_csv(self):
        if not self.history:
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'Ölçümleri kaydet', 'anvil-metrics.csv', 'CSV (*.csv)')
        if filename:
            try:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'cpu_percent', 'cpu_celsius', 'ram_used_bytes', 'gpu_celsius', 'gpu_percent', 'gpu_watts'])
                    for d in self.history:
                        g = d['gpu'] or {}
                        writer.writerow([datetime.fromtimestamp(d['time']).astimezone().isoformat(), d['cpu_usage'], d['cpu_temp'],
                            d['memory_used'], g.get('temperature'), g.get('usage'), g.get('power')])
            except OSError as e:
                QMessageBox.warning(self, 'Kaydedilemedi', str(e))

    def quit_app(self):
        self.close_to_tray.setChecked(False)
        self.close()

    def closeEvent(self, event):
        if self.profile_pending or (self.profile_job and self.profile_job.isRunning()):
            self.profile_feedback.setText('Profil işlemi bitince pencereyi kapatabilirsiniz.')
            self.navigate(2)
            event.ignore()
            return
        if self.close_to_tray.isChecked() and self.tray.isVisible():
            self.hide()
            event.ignore()
            return
        self.timer.stop()
        self.worker.wait()
        self.tray.hide()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Anvil Control')
    configure_style(app)
    window = Window()
    window.show()
    sys.exit(app.exec())
