import csv
import json
import sys
import shutil
from collections import deque
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings, QProcess, QRectF, QPointF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QFileDialog, QMessageBox, QComboBox, QSystemTrayIcon, QMenu,
    QCheckBox, QScrollArea, QLineEdit, QSpinBox, QGraphicsOpacityEffect, QDialog, QDialogButtonBox, QColorDialog)
from .backend import Monitor, set_profile
from .widgets import Meter, FanRotor
from .insights import ThermalAlerts, SensorStats
from . import __version__
from .fans import channels, supports_fan_write
from .rgb import parse_devices

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
QLineEdit, QSpinBox { background:#25241e; padding:9px; border:1px solid #484332; border-radius:6px; selection-background-color:#7a651c; }
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
        self.setMinimumSize(300, 210)
        self.setAccessibleName('Anakartın temsili bileşen şeması')
        self.temperature = None
        self.pulse = 0.0
        self.motion = True
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(800)
        self.animation.valueChanged.connect(self.animate)

    def animate(self, value):
        self.pulse = float(value)
        self.update()

    def set_temperature(self, value):
        self.temperature = value
        self.animation.stop()
        if self.motion and self.isVisible():
            self.animation.setStartValue(1.0)
            self.animation.setEndValue(0.0)
            self.animation.start()
        self.update()

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
        block(116, 43, 87, 80, 'CPU\n' + fmt(self.temperature, ' °C'), True)
        if self.pulse > 0:
            color = QColor('#ffd438')
            color.setAlphaF(self.pulse * 0.7)
            p.setPen(QPen(color, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(111, 38, 97, 90), 6, 6)
        for x in [225, 244]:
            block(x, 32, 14, 110, '', True)
        p.setPen(QColor('#c3c3af'))
        p.drawText(QRectF(218, 11, 55, 16), Qt.AlignmentFlag.AlignCenter, 'RAM')
        block(278, 48, 10, 72)
        for y in [29, 62, 96]:
            block(43, y, 32, 25, 'I/O')
        for x in range(90, 207, 17):
            block(x, 22, 11, 10)
        for y in range(49, 121, 18):
            block(89, y, 13, 12)
        block(94, 150, 114, 10, 'STORAGE')
        block(81, 174, 158, 14, 'PCIe', True)
        block(81, 205, 66, 11, 'EXPANSION')
        block(223, 198, 38, 26, 'CHIP')
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
        self.caption = 'CPU %'
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
        p.drawText(40, self.height()-4, self.caption + '   •   Son 120 ölçüm (0–100)')
        if len(self.values) > 1:
            path = QPainterPath()
            drawing = False
            for i, value in enumerate(self.values):
                if value is None:
                    drawing = False
                    continue
                x = bounds.left() + i*bounds.width()/119
                y = bounds.bottom() - max(0, min(100, value))*bounds.height()/100
                if not drawing:
                    path.moveTo(x, y)
                    drawing = True
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
        self.setWindowTitle('Anvil Control • ASUS')
        self.resize(1280, 1000)
        self.setMinimumSize(940, 680)
        self.settings = QSettings('Anvil', 'AnvilControl')
        self.motion = self.settings.value('motion', True, type=bool)
        self.stats = SensorStats()
        self.alerts = ThermalAlerts()
        self.events = deque(maxlen=100)
        self.paused = False
        self.monitor = Monitor()
        self.latest = None
        self.history = deque(maxlen=3600)
        self.profile_job = None
        self.profile_pending = False
        self.hardware_job = None
        self.worker = Worker(self.monitor)
        self.worker.result.connect(self.update_data)
        self.worker.error.connect(self.on_error)
        root = QWidget()
        self.setCentralWidget(root)
        horizontal = QHBoxLayout(root)
        horizontal.setContentsMargins(0, 0, 0, 0)
        side = QFrame()
        side.setObjectName('sidebar')
        side.setFixedWidth(196)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(15, 24, 15, 18)
        sl.addWidget(label('ANVIL', 'brand'))
        sl.addWidget(label('ASUS  /  FEDORA', 'muted'))
        sl.addSpacing(22)
        self.stack = QStackedWidget()
        self.nav = []
        names = ['Genel bakış', 'Sensörler', 'Güç', 'Cihazlar', 'Ayarlar']
        for i, name in enumerate(names):
            b = QPushButton(name)
            b.setObjectName('nav')
            b.setCheckable(True)
            b.clicked.connect(lambda checked=False, n=i: self.navigate(n))
            self.nav.append(b)
            sl.addWidget(b)
        sl.addStretch()
        sl.addWidget(label(self.monitor.identity['board'], 'section'))
        sl.addWidget(label('ASUS algılandı' if self.monitor.identity['asus'] else 'ASUS dışı · genel izleme', 'muted'))
        horizontal.addWidget(side)
        horizontal.addWidget(self.stack, 1)
        self.build_overview()
        self.build_thermal()
        self.build_profiles()
        self.build_rgb()
        self.build_hardware()
        self.build_diagnostics()
        self.build_settings()
        self.fade_effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(self.fade_effect)
        self.fade = QVariantAnimation(self)
        self.fade.setDuration(180)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade.valueChanged.connect(self.fade_effect.setOpacity)
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
        layout.setSpacing(14)
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
        self.board = Motherboard()
        self.board.motion = self.motion
        bv.addWidget(self.board)
        name = label(self.monitor.identity['board'], 'section')
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bv.addWidget(name)
        note = label('Temsili şema · pin bağlantısı değildir', 'muted')
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bv.addWidget(note)
        top.addWidget(board, 1)
        grid = QGridLayout()
        self.cards = {}
        self.meters = {}
        for i, (key, text) in enumerate([('cpu', 'İŞLEMCİ SICAKLIĞI'), ('load', 'CPU KULLANIMI'),
                                       ('gpu', 'GPU SICAKLIĞI'), ('ram', 'BELLEK KULLANIMI')]):
            frame, value = self.card(text, '—')
            grid.addWidget(frame, i//2, i%2)
            self.cards[key] = value
            meter = Meter()
            meter.motion = self.motion
            frame.layout().addWidget(meter)
            self.meters[key] = meter
        top.addLayout(grid, 1)
        l.addLayout(top)
        fan_card = QFrame()
        fan_card.setObjectName('card')
        fv = QVBoxLayout(fan_card)
        fv.setContentsMargins(20, 14, 20, 14)
        fh = QHBoxLayout()
        self.rotor = FanRotor()
        self.rotor.motion = self.motion
        fh.addWidget(self.rotor)
        fh.addWidget(label('Fan merkezi', 'section'))
        fh.addStretch()
        self.gpu_fan = label('GPU FAN  —', 'accent')
        fh.addWidget(self.gpu_fan)
        fv.addLayout(fh)
        self.fan_status = label('Fan arayüzleri taranıyor…')
        fv.addWidget(self.fan_status)
        self.fan_readings = label('', 'accent')
        fv.addWidget(self.fan_readings)
        control_row = QHBoxLayout()
        self.fan_channel = QComboBox()
        self.fan_channel.addItem('Kanal 1', 1)
        self.fan_channel.addItem('Kanal 2', 2)
        control_row.addWidget(self.fan_channel)
        self.fan_controls = []
        for title, action in [('Eğri düzenle', self.edit_curve), ('Tam hız', lambda: self.fan_action('full')),
                              ('Önceki ayarlar', lambda: self.fan_action('restore'))]:
            b = button(title, action)
            control_row.addWidget(b)
            self.fan_controls.append(b)
        fv.addLayout(control_row)
        self.fan_feedback = label('Kontrol desteği denetleniyor…', 'muted')
        fv.addWidget(self.fan_feedback)
        l.addWidget(fan_card)
        self.resources = label('GPU belleği ve depolama okunuyor…', 'accent')
        l.addWidget(self.resources)
        self.alert_banner = label('', 'accent')
        self.alert_banner.hide()
        l.addWidget(self.alert_banner)
        graph_bar = QHBoxLayout()
        graph_bar.addWidget(label('Performans geçmişi', 'section'))
        graph_bar.addStretch()
        self.chart_choice = QComboBox()
        self.chart_choice.addItems(['CPU %', 'GPU %', 'CPU °C', 'GPU °C', 'RAM %'])
        self.chart_choice.currentIndexChanged.connect(self.update_chart)
        graph_bar.addWidget(self.chart_choice)
        self.pause_button = button('Duraklat', self.toggle_pause)
        graph_bar.addWidget(self.pause_button)
        l.addLayout(graph_bar)
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
        self.sensor_search = QLineEdit()
        self.sensor_search.setPlaceholderText('Sensör ara: coretemp, NVMe, fan…')
        self.sensor_search.textChanged.connect(self.render_sensors)
        l.addWidget(self.sensor_search)
        self.sensor_table = table(['Kaynak', 'Sensör', 'Şimdi', 'En düşük', 'En yüksek'])
        self.sensor_table.setMinimumHeight(360)
        l.addWidget(self.sensor_table)
        l.addWidget(button('Min / maks değerlerini sıfırla', self.reset_stats))
        l.addWidget(label('Fan kontrolü ana sayfada. Eğri anakartın denetleyicisine yazılır ve uygulama kapansa da çalışır. Önceki ayarlar düğmesi bu açılıştaki ilk değişiklik öncesine döner.', 'muted'))

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
        l = self.page('Cihazlar', 'Algılanan donanım ve isteğe bağlı RGB kontrolü')
        self.device_layout = l
        l.addWidget(label('OpenRGB tarafından algılanan aygıtlar', 'section'))
        l.addWidget(label('Sadece algılanan cihaz ve desteklediği modlar seçilebilir. Anakartın RGB başlığı için yazılım desteği ayrıca gereklidir.', 'muted'))
        self.rgb_devices = QComboBox()
        self.rgb_devices.currentIndexChanged.connect(self.rgb_selection)
        self.rgb_modes = QComboBox()
        l.addWidget(self.rgb_devices)
        l.addWidget(self.rgb_modes)
        self.rgb_color = '#ffd438'
        self.color_button = button('Renk seç: #ffd438', self.choose_rgb)
        l.addWidget(self.color_button)
        self.rgb_apply = button('Rengi / modu uygula', self.apply_rgb)
        self.rgb_apply.setEnabled(False)
        l.addWidget(self.rgb_apply)
        l.addWidget(button('Cihazları tara', self.scan_rgb))
        self.rgb_status = label('Cihazları tara düğmesiyle mevcut RGB aygıtlarını sorgulayın.', 'muted')
        l.addWidget(self.rgb_status)
        b = button('OpenRGB’yi aç', self.open_rgb)
        b.setEnabled(bool(self.monitor.identity['openrgb']))
        l.addWidget(b)
        l.addWidget(label('OpenRGB bulundu.' if self.monitor.identity['openrgb'] else 'OpenRGB bu sistemde kurulu değil.', 'muted'))
        l.addStretch()

    def build_hardware(self):
        l = self.device_layout
        l.addWidget(label('Donanım', 'section'))
        l.addWidget(label('Seri numarası ve makine kimliği okunmaz.', 'muted'))
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
        l = self.device_layout
        l.addWidget(label('Durum ve tanılama', 'section'))
        l.addWidget(label('Eksik desteği görünür kıl · Raporu paylaşmadan önce incele.', 'muted'))
        self.diagnostics = QTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setMinimumHeight(350)
        l.addWidget(self.diagnostics)
        l.addWidget(label('Oturum olayları', 'section'))
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(140)
        self.event_log.setPlaceholderText('Sıcaklık uyarıları ve profil işlemleri burada görünür.')
        l.addWidget(self.event_log)
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
        motion = QCheckBox('Arayüz animasyonları')
        motion.setChecked(self.motion)
        motion.toggled.connect(self.set_motion)
        l.addWidget(motion)
        self.alert_enabled = QCheckBox('CPU / GPU sıcaklık uyarıları')
        self.alert_enabled.setChecked(self.settings.value('alerts', False, type=bool))
        self.alert_enabled.toggled.connect(self.configure_alerts)
        l.addWidget(self.alert_enabled)
        self.threshold = QSpinBox()
        self.threshold.setRange(50, 105)
        self.threshold.setSuffix(' °C — uyarı eşiği')
        self.threshold.setValue(self.settings.value('threshold', 85, type=int))
        self.threshold.valueChanged.connect(self.configure_alerts)
        l.addWidget(self.threshold)
        l.addWidget(label('Bu eşik kişisel bir bildirim tercihidir; donanımın güvenli sıcaklık sınırı değildir. Tekrarlanan uyarı için sıcaklığın önce eşiğin 5 °C altına düşmesi gerekir. Duraklatıldığında uyarılar da durur.', 'muted'))
        l.addWidget(label('Grafikte son 120 ölçüm; dışa aktarma için bellekte son 3.600 ölçüm tutulur. Uygulama kapanınca geçmiş silinir. Yalnızca dışa aktardığınız kayıtlar diske yazılır.', 'muted'))
        fan_scope = ('Fan yazma: bu sürümde yalnızca doğrulanmış PRIME H610M-K D4.'
                     if supports_fan_write(self.monitor.identity['board'])
                     else 'Fan yazma, her anakart için ayrı doğrulama gerektirir ve burada kapalıdır.')
        l.addWidget(label(f'Anvil Control {__version__} • Alpha\nASUS tarafından geliştirilmemiş bağımsız proje.\n{fan_scope}\nRGB desteği algılanan OpenRGB aygıtlarına bağlıdır.', 'muted'))
        l.addStretch()

    def navigate(self, index):
        self.fade.stop()
        self.stack.setCurrentIndex(index)
        if self.motion:
            self.fade.setStartValue(0.45)
            self.fade.setEndValue(1.0)
            self.fade.start()
        else:
            self.fade_effect.setOpacity(1.0)
        for i, b in enumerate(self.nav):
            b.setChecked(i == index)

    def interval_changed(self, seconds):
        self.settings.setValue('interval', seconds)
        self.timer.setInterval(seconds*1000)

    def set_motion(self, enabled):
        self.motion = enabled
        self.settings.setValue('motion', enabled)
        self.board.motion = enabled
        self.rotor.motion = enabled
        self.rotor.sync()
        for meter in self.meters.values():
            meter.motion = enabled
            if not enabled and meter.animation.state() == QVariantAnimation.State.Running:
                target = meter.animation.endValue()
                meter.animation.stop()
                meter.advance(target)
        if not enabled:
            self.board.animation.stop()
            self.board.animate(0)
            self.fade.stop()
            self.fade_effect.setOpacity(1)

    def configure_alerts(self, *args):
        self.settings.setValue('alerts', self.alert_enabled.isChecked())
        self.settings.setValue('threshold', self.threshold.value())
        self.alerts.active.clear()
        self.alert_banner.hide()

    def log_event(self, text):
        self.events.append(datetime.now().strftime('%H:%M:%S') + '  ' + text)
        self.event_log.setPlainText('\n'.join(reversed(self.events)))

    def check_alerts(self, sample):
        if not self.alert_enabled.isChecked():
            return
        readings = {'CPU': sample['cpu_temp'], 'GPU': (sample['gpu'] or {}).get('temperature')}
        for event in self.alerts.check(readings, self.threshold.value()):
            self.log_event(event)
            if self.tray.isVisible():
                self.tray.showMessage('Anvil · Sıcaklık uyarısı', event, QSystemTrayIcon.MessageIcon.Warning)
        active = sorted(self.alerts.active)
        self.alert_banner.setText('SICAKLIK UYARISI  ·  ' + ', '.join(active) + ' — Cihazlar → Durum bölümünü inceleyin.')
        self.alert_banner.setVisible(bool(active))

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_button.setText('Devam et' if self.paused else 'Duraklat')
        if self.paused:
            self.status.setText('DURAKLATILDI  ·  Son ölçümler gösteriliyor; sıcaklık uyarıları durdu.')
            self.rotor.set_speed(None)
            self.log_event('İzleme duraklatıldı.')
        else:
            self.monitor.previous = None
            self.log_event('İzleme devam ediyor.')
            self.refresh()

    def update_chart(self, *args):
        index = self.chart_choice.currentIndex()
        values = []
        for d in list(self.history)[-120:]:
            gpu = d['gpu'] or {}
            values.append([d['cpu_usage'], gpu.get('usage'), d['cpu_temp'], gpu.get('temperature'),
                           100*d['memory_used']/d['memory_total']][index])
        self.chart.values = deque(values, maxlen=120)
        self.chart.caption = self.chart_choice.currentText()
        self.chart.update()

    def render_sensors(self, *args):
        if not self.latest:
            return
        query = self.sensor_search.text().casefold().strip()
        data = []
        for s in self.latest['sensors']:
            if query and query not in (s['chip']+' '+s['label']+' '+s['unit']).casefold():
                continue
            low, high = self.stats.values.get(s['path'], (s['value'], s['value']))
            data.append((s['chip'], s['label'], *[fmt(v, ' '+s['unit'], 1) for v in [s['value'], low, high]]))
        rows(self.sensor_table, data)

    def reset_stats(self):
        self.stats.values.clear()
        if self.latest:
            self.stats.add(self.latest['sensors'])
        self.render_sensors()
        self.log_event('Sensör min / maks değerleri sıfırlandı.')

    def refresh(self):
        if not self.paused and not self.worker.isRunning():
            self.worker.start()

    def hardware_busy(self):
        return self.hardware_job is not None and self.hardware_job.state() != QProcess.ProcessState.NotRunning

    def run_hardware(self, program, arguments, callback, timeout=0):
        if self.hardware_busy():
            QMessageBox.information(self, 'İşlem sürüyor', 'Önce mevcut donanım işleminin tamamlanmasını bekleyin.')
            return
        job = QProcess(self)
        self.hardware_job = job
        completed = [False]
        timer = QTimer(job)
        timer.setSingleShot(True)
        timer.timeout.connect(job.kill)
        def finish(code, *args):
            if completed[0]:
                return
            completed[0] = True
            timer.stop()
            out = bytes(job.readAllStandardOutput()).decode(errors='replace')
            err = bytes(job.readAllStandardError()).decode(errors='replace')
            self.hardware_job = None
            callback(code == 0, out, err)
            job.deleteLater()
            self.refresh()
        job.finished.connect(finish)
        job.errorOccurred.connect(lambda error: finish(-1) if error == QProcess.ProcessError.FailedToStart else None)
        job.start(program, arguments)
        if timeout:
            timer.start(timeout)

    def edit_curve(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Kanal {self.fan_channel.currentData()} · Otomatik fan eğrisi')
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('Donanım kontrollü eğri: sıcaklıklar artmalı, hız azalmamalı.\nSon iki nokta %100; en yüksek sıcaklık 85 °C.'))
        grid = QGridLayout()
        temps, speeds = [], []
        for row, (temp, speed) in enumerate([(30, 50), (45, 60), (60, 75), (75, 100), (85, 100)]):
            t, s = QSpinBox(), QSpinBox()
            t.setRange(20, 85)
            s.setRange(50, 100)
            t.setSuffix(' °C')
            s.setSuffix(' %')
            t.setValue(temp)
            s.setValue(speed)
            if row >= 3:
                s.setEnabled(False)
            grid.addWidget(t, row, 0)
            grid.addWidget(s, row, 1)
            temps.append(t)
            speeds.append(s)
        layout.addLayout(grid)
        warning = label('', 'accent')
        layout.addWidget(warning)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(dialog.reject)
        def accept():
            points = [[t.value(), s.value()] for t, s in zip(temps, speeds)]
            if any(points[i][0] >= points[i+1][0] or points[i][1] > points[i+1][1] for i in range(4)):
                warning.setText('Sıcaklıklar kesin artmalı, hızlar azalmamalı.')
                return
            dialog.accept()
            self.fan_action('curve', points)
        buttons.accepted.connect(accept)
        layout.addWidget(buttons)
        dialog.exec()

    def fan_action(self, action, points=None):
        helper = '/usr/libexec/anvil-fan-helper'
        if not Path(helper).exists():
            self.fan_feedback.setText('Fan yardımcısı için güncel Anvil RPM paketini kurun.')
            return
        if self.hardware_busy():
            return
        args = [helper, str(self.fan_channel.currentData()), action]
        if points is not None:
            args.append(json.dumps(points))
        self.fan_feedback.setText('Yetkilendirme / donanıma yazma bekleniyor…')
        def done(ok, out, err):
            message = 'Fan ayarı uygulandı ve donanımdan geri okunarak doğrulandı.' if ok else 'Fan işlemi başarısız: ' + (err.strip() or 'Yetkilendirme iptal edildi veya yardımcı başlatılamadı.')
            self.fan_feedback.setText(message)
            self.log_event(message)
        self.run_hardware('/usr/bin/pkexec', args, done)

    def choose_rgb(self):
        color = QColorDialog.getColor(QColor(self.rgb_color), self, 'RGB rengi')
        if color.isValid():
            self.rgb_color = color.name()
            self.color_button.setText('Renk seç: ' + self.rgb_color)

    def rgb_selection(self, *args):
        self.rgb_modes.clear()
        item = self.rgb_devices.currentData()
        if item:
            self.rgb_modes.addItems(item['modes'])
        self.rgb_apply.setEnabled(bool(item and item['modes']))

    def scan_rgb(self):
        path = shutil.which('openrgb')
        if not path:
            self.rgb_status.setText('OpenRGB kurulu değil. Fedora paketi: sudo dnf install openrgb')
            return
        if self.hardware_busy():
            return
        self.rgb_apply.setEnabled(False)
        self.rgb_status.setText('RGB aygıtları taranıyor…')
        def done(ok, out, err):
            self.rgb_devices.clear()
            devices = parse_devices(out) if ok else []
            for device in devices:
                self.rgb_devices.addItem(device['name'], device)
            self.rgb_status.setText(f'{len(devices)} aygıt algılandı.' if devices else
                'Kontrol edilebilir RGB aygıtı bulunamadı. Donanım desteği veya aygıt erişimi eksik olabilir.')
            if err.strip() and not devices:
                self.rgb_status.setText(self.rgb_status.text() + '\n' + err.strip()[-600:])
        self.run_hardware(path, ['--list-devices'], done, 30000)

    def apply_rgb(self):
        item = self.rgb_devices.currentData()
        mode = self.rgb_modes.currentText()
        if not item or mode not in item['modes'] or self.hardware_busy():
            return
        self.rgb_status.setText('RGB komutu gönderiliyor…')
        def done(ok, out, err):
            self.rgb_status.setText('OpenRGB komutu tamamlandı; ışıkları cihaz üzerinde kontrol edin.' if ok else 'RGB işlemi başarısız: '+err.strip())
            self.log_event(self.rgb_status.text())
        self.run_hardware(shutil.which('openrgb') or 'openrgb', ['--device', str(item['id']), '--mode', mode, '--color', self.rgb_color[1:]], done, 30000)

    def on_error(self, error):
        self.status.setText('Ölçüm alınamadı: ' + error + ' • Ekrandaki değerler eski olabilir.')

    def update_data(self, d):
        if self.paused:
            return
        self.latest = d
        self.history.append(d)
        gpu = d['gpu'] or {}
        self.stats.add(d['sensors'])
        self.board.set_temperature(d['cpu_temp'])
        self.rotor.set_speed(gpu.get('fan'))
        percentages = {'cpu': d['cpu_temp'], 'load': d['cpu_usage'], 'gpu': gpu.get('temperature'),
                       'ram': 100*d['memory_used']/d['memory_total']}
        for key, meter in self.meters.items():
            meter.set_value(percentages[key])
        vram = (f"{gpu['memory_used']/2**30:.1f} / {gpu['memory_total']/2**30:.1f} GiB"
                if gpu.get('memory_total') else '—')
        self.resources.setText(f"VRAM  {vram}     ·     Disk /  %{100*d['disk_used']/d['disk_total']:.0f} dolu")
        self.check_alerts(d)
        self.cards['cpu'].setText(fmt(d['cpu_temp'], ' °C'))
        self.cards['load'].setText(fmt(d['cpu_usage'], ' %'))
        self.cards['gpu'].setText(fmt(gpu.get('temperature'), ' °C'))
        self.cards['ram'].setText(f"{d['memory_used']/2**30:.1f} / {d['memory_total']/2**30:.1f} GiB")
        self.update_chart()
        stamp = datetime.fromtimestamp(d['time']).strftime('%H:%M:%S')
        self.status.setText(f'●  CANLI   •   Son ölçüm {stamp}   •   {self.monitor.identity["os"]}')
        self.summary.setText(f"{gpu.get('name', 'GPU telemetrisi kullanılamıyor')}\n"
            f"GPU kullanımı {fmt(gpu.get('usage'), ' %')}   ·   Güç {fmt(gpu.get('power'), ' W', 1)}   ·   GPU fanı {fmt(gpu.get('fan'), ' %')}\n"
            f"CPU frekansı {fmt(d['cpu_mhz'], ' MHz')}   ·   Açık kalma {float(d['uptime'])/3600:.1f} saat   ·   Disk / {d['disk_used']/2**30:.0f} / {d['disk_total']/2**30:.0f} GB")
        self.render_sensors()
        fans = [s for s in d['sensors'] if s['unit'] == 'RPM']
        self.gpu_fan.setText('GPU FAN  ' + fmt(gpu.get('fan'), ' %'))
        self.fan_readings.setText('  ·  '.join(f"{s['chip']} / {s['label']}: {s['value']:.0f} RPM" for s in fans))
        self.fan_readings.setVisible(bool(fans))
        pwm = list(Path('/sys/class/hwmon').glob('hwmon*/pwm[0-9]'))
        self.monitor.identity['pwm'] = [str(p) for p in pwm]
        controllable = channels()
        enabled = bool(controllable) and Path('/usr/libexec/anvil-fan-helper').exists() and not self.hardware_busy()
        for b in self.fan_controls:
            b.setEnabled(enabled)
        if not controllable and not supports_fan_write(self.monitor.identity['board']):
            self.fan_feedback.setText('Bu ASUS kartta fan sensörleri okunabilir; güvenli yazma profili henüz doğrulanmadı. Kontroller kapalı.')
        elif not controllable:
            self.fan_feedback.setText('Doğrulanmış kart algılandı, ancak NCT6798 fan arayüzü görünmüyor. nct6775 sürücüsünü kontrol edin.')
        elif not Path('/usr/libexec/anvil-fan-helper').exists():
            self.fan_feedback.setText('Fan denetleyicisi bulundu. Kontrol için güncel RPM paketini kurun.')
        elif self.fan_feedback.text() == 'Kontrol desteği denetleniyor…':
            self.fan_feedback.setText('Otomatik eğri / tam hız hazır. Kanal numaraları fiziksel CPU/kasa etiketi değildir.')
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
            'FAN KONTROLÜ\n' + self.fan_status.text() + '\n' + self.fan_feedback.text(),
            'GPU\n' + (gpu.get('name', '') + ' • NVIDIA NVML ile okunuyor.' if gpu else 'NVML telemetrisi alınamadı. Donanım ekranından sürücüyü inceleyin.'),
            'GÜÇ PROFİLLERİ\n' + (', '.join(available) if available else 'Güç profili servisine erişilemiyor.'),
            'RGB\n' + self.rgb_status.text(),
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
        self.log_event(self.profile_feedback.text())
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
                Path(filename).write_text(json.dumps({'version':__version__, 'hardware':self.monitor.identity,
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
        if self.hardware_busy():
            QMessageBox.information(self, 'Donanım işlemi', 'Donanım işlemi veya yetkilendirme tamamlandıktan sonra kapatın.')
            event.ignore()
            return
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
