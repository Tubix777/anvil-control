import csv
import json
import math
import re
import sys
import shutil
from collections import deque
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings, QProcess, QRectF, QPointF, QVariantAnimation, QEasingCurve, QSignalBlocker
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPainterPath, QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QFileDialog, QMessageBox, QComboBox, QSystemTrayIcon, QMenu,
    QCheckBox, QScrollArea, QLineEdit, QSpinBox, QGraphicsOpacityEffect, QDialog, QDialogButtonBox, QColorDialog)
from .backend import Monitor, set_profile
from .widgets import Meter, FanRotor
from .insights import ThermalAlerts, SensorStats
from . import __version__
from .fans import channels, supports_fan_write, fan_result, FAN_PRESETS, preset_points
from .compat import capability_report
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
QComboBox QAbstractItemView { background:#191917; color:#f2f1ec; border:1px solid #35332b; selection-background-color:#7a651c; }
QScrollArea { border:0; }
QLineEdit, QSpinBox { background:#25241e; padding:9px; border:1px solid #484332; border-radius:6px; selection-background-color:#7a651c; }
QToolTip { background:#25241e; color:#f2f1ec; border:1px solid #ffd438; }
QMenu { background:#191917; color:#f2f1ec; border:1px solid #35332b; }
QMenu::item:selected { background:#3b3520; color:#ffd438; }
'''


DEFAULT_THEME = 'anvil'
THEME_NAMES = {
    'anvil': 'Anvil Sarı',
    'night': 'Gece Mavisi',
    'forest': 'Orman Yeşili',
    'copper': 'Bakır Kızılı',
    'violet': 'Mor Gece',
    'graphite': 'Grafit',
    'daylight': 'Gün Işığı',
}
THEMES = {
    'anvil': dict(background='#101010', foreground='#f2f1ec', sidebar='#090909',
        sidebar_border='#2d2b23', card='#191917', border='#35332b', accent='#ffd438',
        muted='#b3b0a3', on_accent='#111111', button='#25241e', button_border='#484332',
        hover='#3b3520', disabled_text='#817e71', disabled_bg='#1c1c19', table='#171715',
        grid='#302e27', header='#26251f', header_text='#ccc7b4', selection='#7a651c',
        board_bg='#11120f', board_border='#807038', trace='#383722', block_accent='#35301c',
        block='#242520', block_accent_border='#e0bb36', block_border='#64644f',
        block_accent_text='#ffe178', block_text='#c3c3af', hole_border='#82794d',
        meter_track='#343127', rotor_ring='#615a38', rotor_disabled='#777264'),
    'night': dict(background='#0b1420', foreground='#edf5fb', sidebar='#07111c',
        sidebar_border='#253d52', card='#122332', border='#31485a', accent='#6fd2ff',
        muted='#a8bccb', on_accent='#07111c', button='#1a3042', button_border='#375872',
        hover='#244a60', disabled_text='#7a91a0', disabled_bg='#10202c', table='#112130',
        grid='#254053', header='#1b3446', header_text='#c4d4df', selection='#245874',
        board_bg='#0c1b29', board_border='#4984a6', trace='#22465b', block_accent='#1f465d',
        block='#1b3140', block_accent_border='#7ad9ff', block_border='#578098',
        block_accent_text='#b6edff', block_text='#ccdfe9', hole_border='#4d819b',
        meter_track='#263d4b', rotor_ring='#476b80', rotor_disabled='#7d929d'),
    'forest': dict(background='#0d1511', foreground='#eaf5ea', sidebar='#09110d',
        sidebar_border='#294237', card='#17251d', border='#355343', accent='#a8ed86',
        muted='#b3c5b4', on_accent='#102012', button='#213329', button_border='#48664f',
        hover='#2d4b35', disabled_text='#829387', disabled_bg='#19251c', table='#16231b',
        grid='#2e4835', header='#24392b', header_text='#cddccb', selection='#476b34',
        board_bg='#101d15', board_border='#608668', trace='#365b3f', block_accent='#315039',
        block='#26392b', block_accent_border='#b5f299', block_border='#6d9471',
        block_accent_text='#d3ffc2', block_text='#d1e4cf', hole_border='#729375',
        meter_track='#304a34', rotor_ring='#5c8060', rotor_disabled='#879d88'),
}

THEMES.update({
    'copper': dict(THEMES['anvil'], background='#17110e', foreground='#f9eee5',
        sidebar='#100c0b', sidebar_border='#523428', card='#241914', border='#664434',
        accent='#ffad65', muted='#ceb2a0', on_accent='#251208', button='#35251d',
        button_border='#76503b', hover='#513323', disabled_text='#9b7d6b',
        disabled_bg='#281d18', table='#211813', grid='#4f3428', header='#38251c',
        header_text='#e5c9b4', selection='#84512d', board_bg='#1d1510',
        board_border='#a46a46', trace='#573929', block_accent='#603a25',
        block='#37261c', block_accent_border='#ffba7f', block_border='#a16b4a',
        block_accent_text='#ffe1c3', block_text='#e5cbb9', hole_border='#ad7350',
        meter_track='#513629', rotor_ring='#986444', rotor_disabled='#a08876'),
    'violet': dict(THEMES['anvil'], background='#15101e', foreground='#f3edff',
        sidebar='#100b17', sidebar_border='#3b2b52', card='#21182e', border='#503866',
        accent='#c7a4ff', muted='#c2b3d4', on_accent='#190d29', button='#30223f',
        button_border='#684d82', hover='#48315f', disabled_text='#9482a7',
        disabled_bg='#241b30', table='#1d1628', grid='#423050', header='#31243e',
        header_text='#dacbea', selection='#654683', board_bg='#191322',
        board_border='#8060a2', trace='#423052', block_accent='#4d3468',
        block='#30243e', block_accent_border='#d3b6ff', block_border='#775b90',
        block_accent_text='#e7d4ff', block_text='#d7c7e6', hole_border='#9274af',
        meter_track='#463351', rotor_ring='#765991', rotor_disabled='#9382a1'),
    'graphite': dict(THEMES['anvil'], background='#111417', foreground='#e9edf0',
        sidebar='#0c1013', sidebar_border='#343c42', card='#1b2227', border='#45515a',
        accent='#e4e8ed', muted='#aebbc5', on_accent='#151a1e', button='#293239',
        button_border='#57636c', hover='#3d4a52', disabled_text='#87939b',
        disabled_bg='#20282d', table='#1b2227', grid='#364149', header='#2d383f',
        header_text='#d0d9de', selection='#52626b', board_bg='#151c20',
        board_border='#83939e', trace='#3e4b54', block_accent='#485861',
        block='#2b363d', block_accent_border='#dce6eb', block_border='#819099',
        block_accent_text='#f1f7f9', block_text='#d4dfe4', hole_border='#91a1aa',
        meter_track='#3b474e', rotor_ring='#77878f', rotor_disabled='#89949a'),
    'daylight': dict(THEMES['anvil'], background='#f3f2ed', foreground='#202a30',
        sidebar='#e6e8e5', sidebar_border='#c4cfcd', card='#ffffff', border='#b6c6c8',
        accent='#156b8a', muted='#4b5f69', on_accent='#ffffff', button='#e6edf0',
        button_border='#9cb2bc', hover='#d5e5eb', disabled_text='#65747c',
        disabled_bg='#e9eceb', table='#ffffff', grid='#d4e0e3', header='#dce9ec',
        header_text='#314951', selection='#b7d6e2', board_bg='#eef5f5',
        board_border='#6e9dad', trace='#aacbd3', block_accent='#b6dbe4',
        block='#d6e5e8', block_accent_border='#277d99', block_border='#769ca7',
        block_accent_text='#154f63', block_text='#30515a', hole_border='#6e9eab',
        meter_track='#cadadf', rotor_ring='#739ba7', rotor_disabled='#84979b'),
})

STYLE_COLOR_ROLES = {
    '#101010': 'background', '#f2f1ec': 'foreground', '#090909': 'sidebar',
    '#2d2b23': 'sidebar_border', '#191917': 'card', '#35332b': 'border',
    '#ffd438': 'accent', '#b3b0a3': 'muted', '#111111': 'on_accent',
    '#25241e': 'button', '#484332': 'button_border', '#3b3520': 'hover',
    '#817e71': 'disabled_text', '#1c1c19': 'disabled_bg', '#171715': 'table',
    '#302e27': 'grid', '#26251f': 'header', '#ccc7b4': 'header_text',
    '#7a651c': 'selection',
}


def resolve_theme(key):
    return key if key in THEMES else DEFAULT_THEME


def style_for_theme(key):
    colors = THEMES[resolve_theme(key)]
    return re.sub(r'#[0-9a-fA-F]{6}',
                  lambda match: colors[STYLE_COLOR_ROLES[match.group(0).lower()]], STYLE)


def configure_style(app, theme=DEFAULT_THEME):
    family = next((name for name in ['Adwaita Sans', 'Noto Sans', 'DejaVu Sans']
                   if name in QFontDatabase.families()), 'Sans Serif')
    font = QFont(family, 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    app.setStyle('Fusion')
    app.setStyleSheet(style_for_theme(theme))


class Motherboard(QWidget):
    """Original component diagram, not an electrical or pinout reference."""
    TRACE_ROUTES = (
        ((207, 101), (221, 101), (221, 172), (249, 172)),
        ((125, 152), (125, 161), (208, 161), (208, 180), (255, 180)),
        ((211, 69), (224, 69), (224, 40), (281, 40), (281, 91)),
    )

    def __init__(self):
        super().__init__()
        self.setMinimumSize(320, 220)
        self.setAccessibleName('Anakartın temsili bileşen şeması')
        self.setToolTip('Temsili üstten görünüş. Işık hareketleri dekoratiftir; pin şeması veya gerçek sinyal akışı değildir.')
        self.temperature = None
        self.pulse = 0.0
        self.phase = 0.0
        self.motion = True
        self.theme = THEMES[DEFAULT_THEME]
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(800)
        self.animation.valueChanged.connect(self.animate)
        self.timer = QTimer(self)
        self.timer.setInterval(70)
        self.timer.timeout.connect(self.tick)

    @staticmethod
    def trace_position(points, progress):
        lengths = [math.hypot(b[0]-a[0], b[1]-a[1]) for a, b in zip(points, points[1:])]
        remaining = (progress % 1.0) * sum(lengths)
        for (a, b), length in zip(zip(points, points[1:]), lengths):
            if remaining <= length:
                fraction = remaining / length if length else 0
                return QPointF(a[0] + (b[0]-a[0])*fraction, a[1] + (b[1]-a[1])*fraction)
            remaining -= length
        return QPointF(*points[-1])

    def tick(self):
        self.phase = (self.phase + 0.018) % 1.0
        self.update()

    def sync_motion(self):
        if self.motion and self.isVisible():
            self.timer.start()
        else:
            self.timer.stop()

    def set_motion(self, enabled):
        self.motion = enabled
        self.sync_motion()
        if not enabled:
            self.animation.stop()
            self.pulse = 0.0
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_motion()

    def hideEvent(self, event):
        self.timer.stop()
        self.animation.stop()
        super().hideEvent(event)

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
        colors = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = min(self.width()/350, self.height()/250)
        p.translate((self.width()-350*scale)/2, (self.height()-250*scale)/2)
        p.scale(scale, scale)
        def panel(x, y, w, h, fill, border, radius=3, width=1):
            p.setBrush(QColor(fill))
            p.setPen(QPen(QColor(border), width))
            p.drawRoundedRect(QRectF(x, y, w, h), radius, radius)

        def caption(text, x, y, w, h, size=8, color='block_text'):
            font = QFont(self.font())
            font.setPixelSize(size)
            font.setWeight(QFont.Weight.DemiBold)
            p.setFont(font)
            p.setPen(QColor(colors[color]))
            p.drawText(QRectF(x, y, w, h), Qt.AlignmentFlag.AlignCenter, text)

        shadow = QColor(colors['accent'])
        shadow.setAlpha(18)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shadow)
        p.drawRoundedRect(QRectF(14, 11, 322, 233), 15, 15)
        board_fill = QLinearGradient(18, 8, 330, 240)
        board_fill.setColorAt(0, QColor(colors['board_bg']).lighter(113))
        board_fill.setColorAt(1, QColor(colors['board_bg']))
        p.setBrush(board_fill)
        p.setPen(QPen(QColor(colors['board_border']), 1.6))
        p.drawRoundedRect(QRectF(18, 7, 314, 231), 12, 12)
        p.setBrush(Qt.BrushStyle.NoBrush)
        inner = QColor(colors['board_border'])
        inner.setAlpha(65)
        p.setPen(QPen(inner, 0.8))
        p.drawRoundedRect(QRectF(23, 12, 304, 221), 9, 9)

        for row in range(6):
            for col in range(10):
                p.setPen(Qt.PenStyle.NoPen)
                dot = QColor(colors['trace'])
                dot.setAlpha(105)
                p.setBrush(dot)
                p.drawEllipse(QRectF(69 + col*24, 48 + row*29, 1.5, 1.5))

        for index, points in enumerate(self.TRACE_ROUTES):
            poly = [QPointF(*point) for point in points]
            trace = QColor(colors['trace'])
            trace.setAlpha(210)
            p.setPen(QPen(trace, 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolyline(poly)
            if self.motion:
                spot = self.trace_position(points, self.phase + index/3)
                halo = QColor(colors['accent'])
                halo.setAlpha(45)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(halo)
                p.drawEllipse(spot, 5, 5)
                halo.setAlpha(210)
                p.setBrush(halo)
                p.drawEllipse(spot, 1.7, 1.7)

        caption('ANVIL  /  BOARD VIEW', 45, 13, 131, 13, 8, 'block_accent_text')
        caption('VRM', 72, 31, 27, 12, 7)
        for x in range(104, 203, 17):
            panel(x, 31, 12, 14, colors['block'], colors['block_border'], 2)
            panel(x+2, 33, 8, 3, colors['block_accent'], colors['trace'], 1)
        for y in range(60, 145, 18):
            panel(75, y, 18, 14, colors['block'], colors['block_border'], 2)
            panel(78, y+3, 12, 3, colors['block_accent'], colors['trace'], 1)

        for y in (43, 75, 107):
            panel(21, y, 36, 25, colors['block'], colors['block_border'], 3)
            panel(25, y+5, 28, 15, colors['board_bg'], colors['hole_border'], 2)
            caption('I/O', 27, y+6, 24, 13, 7)
        for y in (52, 72, 92, 112, 132):
            panel(61, y, 8, 10, colors['block_accent'], colors['block_border'], 1)

        panel(104, 50, 109, 108, colors['block'], colors['block_border'], 8, 1.5)
        panel(110, 56, 97, 96, colors['board_bg'], colors['hole_border'], 6)
        for x in range(118, 202, 10):
            panel(x, 52, 5, 3, colors['block_border'], colors['block_border'], 1)
            panel(x, 153, 5, 3, colors['block_border'], colors['block_border'], 1)
        for y in range(62, 146, 10):
            panel(106, y, 3, 5, colors['block_border'], colors['block_border'], 1)
            panel(208, y, 3, 5, colors['block_border'], colors['block_border'], 1)
        panel(120, 66, 77, 76, colors['block_accent'], colors['block_accent_border'], 5, 1.8)
        glow = QColor(colors['accent'])
        glow.setAlpha(int(22 + (32 if self.motion else 0) * (1 + math.sin(self.phase*2*math.pi))/2 + 110*self.pulse))
        p.setPen(QPen(glow, 2.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(116, 62, 85, 84), 7, 7)
        caption('CPU', 132, 85, 53, 19, 13, 'block_accent_text')
        caption(fmt(self.temperature, ' °C'), 128, 106, 61, 19, 13, 'block_accent_text')

        caption('DDR', 230, 20, 53, 13, 8)
        for x in (234, 258):
            panel(x-3, 36, 20, 128, colors['block'], colors['block_border'], 3)
            panel(x, 41, 14, 114, colors['block_accent'], colors['block_accent_border'], 2)
            for y in range(48, 149, 14):
                panel(x+2, y, 10, 5, colors['block'], colors['trace'], 1)
            for y in (38, 158):
                panel(x+3, y, 8, 4, colors['block_accent_border'], colors['block_accent_border'], 1)

        panel(90, 165, 120, 12, colors['block'], colors['block_border'], 2)
        panel(100, 168, 92, 5, colors['block_accent'], colors['trace'], 1)
        caption('M.2', 147, 166, 34, 9, 7, 'block_accent_text')
        panel(74, 187, 179, 16, colors['block_accent'], colors['block_accent_border'], 2)
        panel(80, 190, 163, 6, colors['board_bg'], colors['board_border'], 1)
        panel(131, 189, 5, 10, colors['block_accent_border'], colors['block_accent_border'], 1)
        caption('PCIe x16', 80, 206, 70, 11, 8)
        panel(76, 218, 72, 8, colors['block'], colors['block_border'], 2)
        for x in (84, 96, 108, 120, 132):
            panel(x, 220, 5, 4, colors['block_accent'], colors['trace'], 1)

        panel(280, 123, 36, 42, colors['block'], colors['block_border'], 3)
        for y in (130, 146):
            panel(284, y, 28, 12, colors['board_bg'], colors['hole_border'], 2)
        caption('SATA', 282, 107, 34, 12, 7)
        panel(271, 177, 46, 45, colors['block_accent'], colors['block_accent_border'], 6)
        for offset in range(4, 34, 7):
            line = QColor(colors['block_accent_border'])
            line.setAlpha(105)
            p.setPen(QPen(line, 1))
            p.drawLine(277+offset, 184, 277+offset, 200)
        caption('CHIPSET', 275, 204, 38, 12, 7, 'block_accent_text')
        panel(290, 50, 25, 18, colors['block'], colors['block_border'], 2)
        caption('FAN', 291, 70, 23, 10, 7)
        for x, y in ((31, 20), (319, 20), (31, 224), (319, 224)):
            p.setPen(QPen(QColor(colors['hole_border']), 2))
            p.setBrush(QColor(colors['background']))
            p.drawEllipse(QRectF(x-4, y-4, 8, 8))
            p.setPen(QPen(QColor(colors['block_border']), 1))
            p.drawLine(x-2, y, x+2, y)
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


def fan_channel_label(item):
    """Use only the controller's channel number, never an unverified socket name."""
    rpm = item.get('rpm')
    reading = f'{rpm:.0f} RPM' if isinstance(rpm, (int, float)) and math.isfinite(rpm) and rpm >= 0 else 'RPM okunamadı'
    return f"Kanal {item['channel']} · {reading}"


def preferred_fan_channel(items, selected=None):
    """Keep a selection; otherwise prefer a fan only when exactly one spins."""
    if selected in [item['channel'] for item in items]:
        return selected
    spinning = [item for item in items if isinstance(item.get('rpm'), (int, float))
                and math.isfinite(item['rpm']) and item['rpm'] > 0]
    if len(spinning) == 1:
        return spinning[0]['channel']
    return items[0]['channel'] if items else None


def hardware_fan_curve_text(item):
    """Describe read-back PWM points separately from the preset preview."""
    if item is None:
        return 'Seçili kanalın donanım eğrisi okunamıyor. Hazır eğriler yalnızca önizlemedir.'
    prefix = f"Kanal {item['channel']} · Donanımdan okunan "
    mode = item.get('mode')
    state = 'etkin otomatik eğri' if mode == '5' else 'kayıtlı eğri (şu an tam hız etkin)' if mode == '0' else 'eğri'
    details = []
    source_temp = item.get('source_temp')
    if isinstance(source_temp, (int, float)) and math.isfinite(source_temp):
        details.append(f"Sıcaklık kaynağı: {item.get('source_label') or 'PECI'} {source_temp:g} °C")
    up, down = item.get('step_up_ms'), item.get('step_down_ms')
    if all(isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 for value in (up, down)):
        details.append(f'Fan tepki süresi: hızlanma {up:g} ms / yavaşlama {down:g} ms'
                       + (' (gecikme yok)' if up == down == 0 else ''))
    points = item.get('points')
    if (not isinstance(points, (list, tuple)) or len(points) != 5
            or any(not isinstance(point, (list, tuple)) or len(point) != 2
                   or any(not isinstance(value, (int, float)) or not math.isfinite(value)
                          for value in point) for point in points)):
        return prefix + state + ': beş noktanın tamamı okunamadı.' + ('\n' + ' · '.join(details) if details else '')
    values = '  ·  '.join(f'{temp:g} °C → ≈%{speed:.0f}' for temp, speed in points)
    return prefix + state + ' (PWM yüzdesi yaklaşık):\n' + values + ('\n' + ' · '.join(details) if details else '')


def percent(part, total):
    return 100 * part / total if part is not None and total and total > 0 else None


def hours(value):
    try:
        return f'{float(value)/3600:.1f}'
    except (TypeError, ValueError):
        return '—'


class Chart(QWidget):
    def __init__(self):
        super().__init__()
        self.values = deque(maxlen=120)
        self.caption = 'CPU %'
        self.theme = THEMES[DEFAULT_THEME]
        self.motion = True
        self.highlight = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(700)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self.animate_highlight)
        self.setMinimumHeight(100)

    def animate_highlight(self, value):
        self.highlight = float(value)
        self.update()

    def pulse_latest(self):
        self.animation.stop()
        if self.motion and self.isVisible() and self.values and self.values[-1] is not None:
            self.animation.setStartValue(1.0)
            self.animation.setEndValue(0.0)
            self.animation.start()
        else:
            self.highlight = 0.0
            self.update()

    def set_motion(self, enabled):
        self.motion = enabled
        if not enabled:
            self.animation.stop()
            self.highlight = 0.0
            self.update()

    def hideEvent(self, event):
        self.animation.stop()
        self.highlight = 0.0
        super().hideEvent(event)

    def paintEvent(self, event):
        colors = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = self.rect().adjusted(40, 16, -12, -28)
        p.setPen(QColor(colors['border']))
        for n in range(5):
            y = bounds.bottom() - n * bounds.height()/4
            p.setPen(QColor(colors['border']))
            p.drawLine(bounds.left(), int(y), bounds.right(), int(y))
            p.setPen(QColor(colors['muted']))
            p.drawText(0, int(y)+4, str(n*25))
        p.setPen(QColor(colors['muted']))
        p.drawText(40, self.height()-4, self.caption + '   •   Son 120 ölçüm (0–100)')
        if len(self.values) > 1:
            path = QPainterPath()
            drawing = False
            endpoint = None
            for i, value in enumerate(self.values):
                if value is None:
                    drawing = False
                    endpoint = None
                    continue
                x = bounds.left() + i*bounds.width()/119
                y = bounds.bottom() - max(0, min(100, value))*bounds.height()/100
                endpoint = QPointF(x, y)
                if not drawing:
                    path.moveTo(x, y)
                    drawing = True
                else:
                    path.lineTo(x, y)
            p.setPen(QPen(QColor(colors['accent']), 2.5))
            p.drawPath(path)
            if endpoint is not None:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(colors['accent']))
                p.drawEllipse(endpoint, 3, 3)
                if self.highlight > 0:
                    halo = QColor(colors['accent'])
                    halo.setAlpha(int(170*self.highlight))
                    p.setPen(QPen(halo, 1.8))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    radius = 4 + 7*(1-self.highlight)
                    p.drawEllipse(endpoint, radius, radius)
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
        self.theme_key = resolve_theme(self.settings.value('theme', DEFAULT_THEME, type=str))
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
        sl.addSpacing(18)
        sl.addWidget(label('TEMA SEÇ', 'accent'))
        self.quick_theme = QComboBox()
        self.quick_theme.setAccessibleName('Tema seçimi')
        for key, name in THEME_NAMES.items():
            self.quick_theme.addItem(name, key)
        self.quick_theme.setCurrentIndex(self.quick_theme.findData(self.theme_key))
        self.quick_theme.currentIndexChanged.connect(lambda: self.apply_theme(self.quick_theme.currentData()))
        sl.addWidget(self.quick_theme)
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
        self.apply_theme(self.theme_key, persist=False)
        self.fade_effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(self.fade_effect)
        self.fade = QVariantAnimation(self)
        self.fade.setDuration(180)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade.valueChanged.connect(self.fade_effect.setOpacity)
        self.navigate(0)
        self.tray = QSystemTrayIcon(QIcon.fromTheme('io.anvil.Control', QIcon.fromTheme('computer')), self)
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
        self.compatibility = label('Model ve kullanılabilir özellikler algılanıyor…', 'accent')
        l.addWidget(self.compatibility)
        top = QHBoxLayout()
        board = QFrame()
        board.setObjectName('card')
        bv = QVBoxLayout(board)
        bv.setContentsMargins(14, 10, 14, 14)
        self.board = Motherboard()
        self.board.set_motion(self.motion)
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
        self.fan_channel.addItem('Kanal aranıyor…', None)
        self.fan_channel.setEnabled(False)
        self.fan_channel.setAccessibleName('Fan kanalı ve canlı devir')
        self.fan_channel.setToolTip('Kanal numarası fiziksel CPU/kasa etiketi değildir; RPM denetleyici sensöründen okunur.')
        self.current_fan_channels = []
        self.fan_channel.currentIndexChanged.connect(self.update_current_fan_curve)
        control_row.addWidget(self.fan_channel)
        self.fan_controls = []
        for title, action in [('Eğri düzenle', self.edit_curve), ('Tam hız', lambda: self.fan_action('full')),
                              ('Önceki ayarlar', lambda: self.fan_action('restore'))]:
            b = button(title, action)
            control_row.addWidget(b)
            self.fan_controls.append(b)
        fv.addLayout(control_row)
        self.fan_curve_info = label('Seçili kanalın donanım eğrisi okunuyor…', 'muted')
        self.fan_curve_info.setAccessibleName('Seçili fan kanalının donanım eğrisi')
        fv.addWidget(self.fan_curve_info)
        preset_row = QHBoxLayout()
        preset_row.addWidget(label('Hazır hız eğrisi', 'section'))
        self.preset_combo = QComboBox()
        for key, (name, _) in FAN_PRESETS.items():
            self.preset_combo.addItem(name, key)
        self.preset_combo.currentIndexChanged.connect(self.update_preset_info)
        preset_row.addWidget(self.preset_combo, 1)
        self.preset_apply = button('Eğriyi uygula', self.apply_fan_preset)
        self.preset_apply.setEnabled(False)
        self.fan_controls.append(self.preset_apply)
        preset_row.addWidget(self.preset_apply)
        fv.addLayout(preset_row)
        self.preset_info = label('', 'muted')
        fv.addWidget(self.preset_info)
        fv.addWidget(label('Fan eğrileri etkin yerel oturumda şifre sormadan uygulanır; yalnızca doğrulanmış kart ve kanallar desteklenir.', 'muted'))
        self.update_preset_info()
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
        self.chart.set_motion(self.motion)
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
        l.addWidget(label('Bu sistemde kullanılabilir özellikler', 'section'))
        l.addWidget(label('ASUS modellerinde izleme otomatik algılanır; fan yazma için fiziksel doğrulama gerekir.', 'muted'))
        self.capability_table = table(['Özellik', 'Algılanan durum'])
        self.capability_table.setMinimumHeight(270)
        l.addWidget(self.capability_table)
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
        l.addWidget(label('Görünüm', 'section'))
        self.theme_combo = QComboBox()
        for key, name in THEME_NAMES.items():
            self.theme_combo.addItem(name, key)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(self.theme_key))
        self.theme_combo.currentIndexChanged.connect(lambda: self.apply_theme(self.theme_combo.currentData()))
        l.addWidget(self.theme_combo)
        l.addWidget(label('Tema sol menüdeki TEMA SEÇ alanından da değiştirilebilir; tercih sonraki açılışta korunur.', 'muted'))
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
        fan_scope = ('Fan yazma: bu kartta doğrulanmış profil algılandı; güvenli kanal da gerekli.'
                     if supports_fan_write(self.monitor.identity['board'], self.monitor.identity['vendor'])
                     else 'Fan yazma, her anakart için ayrı doğrulama gerektirir ve burada kapalıdır.')
        l.addWidget(label(f'Anvil Control {__version__} • Alpha\nASUS tarafından geliştirilmemiş bağımsız proje.\n{fan_scope}\nRGB desteği algılanan OpenRGB aygıtlarına bağlıdır.', 'muted'))
        l.addStretch()

    def apply_theme(self, key, persist=True):
        self.theme_key = resolve_theme(key)
        if persist:
            self.settings.setValue('theme', self.theme_key)
        for selector in (self.quick_theme, self.theme_combo):
            index = selector.findData(self.theme_key)
            if selector.currentIndex() != index:
                with QSignalBlocker(selector):
                    selector.setCurrentIndex(index)
        colors = THEMES[self.theme_key]
        QApplication.instance().setStyleSheet(style_for_theme(self.theme_key))
        self.board.theme = colors
        self.board.update()
        self.chart.theme = colors
        self.chart.update()
        for meter in self.meters.values():
            meter.accent_color = colors['accent']
            meter.track_color = colors['meter_track']
            meter.update()
        self.rotor.accent_color = colors['accent']
        self.rotor.ring_color = colors['rotor_ring']
        self.rotor.disabled_color = colors['rotor_disabled']
        self.rotor.update()

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
        self.board.set_motion(enabled)
        self.chart.set_motion(enabled)
        self.rotor.motion = enabled
        self.rotor.sync()
        for meter in self.meters.values():
            meter.motion = enabled
            if not enabled and meter.animation.state() == QVariantAnimation.State.Running:
                target = meter.animation.endValue()
                meter.animation.stop()
                meter.advance(target)
        if not enabled:
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
                           percent(d['memory_used'], d['memory_total'])][index])
        self.chart.values = deque(values, maxlen=120)
        self.chart.caption = self.chart_choice.currentText()
        self.chart.pulse_latest()

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
        channel = self.fan_channel.currentData()
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Kanal {channel} · Otomatik fan eğrisi')
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('Donanım kontrollü eğri: sıcaklıklar artmalı, hız azalmamalı.\nSon iki nokta %100; en yüksek sıcaklık 85 °C.'))
        grid = QGridLayout()
        temps, speeds = [], []
        points = preset_points(self.preset_combo.currentData()) or [[30, 50], [45, 60], [60, 75], [75, 100], [85, 100]]
        for row, (temp, speed) in enumerate(points):
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
            if self.fan_channel.currentData() != channel:
                warning.setText('Fan kanalı değişti. Bu pencereyi kapatıp seçili kanal için yeniden açın.')
                return
            points = [[t.value(), s.value()] for t, s in zip(temps, speeds)]
            if any(points[i][0] >= points[i+1][0] or points[i][1] > points[i+1][1] for i in range(4)):
                warning.setText('Sıcaklıklar kesin artmalı, hızlar azalmamalı.')
                return
            dialog.accept()
            self.fan_action('curve', points, expected_channel=channel)
        buttons.accepted.connect(accept)
        layout.addWidget(buttons)
        dialog.exec()

    def update_preset_info(self, *args):
        points = preset_points(self.preset_combo.currentData())
        if points:
            self.preset_info.setText(' · '.join(f'{temp} °C → %{speed}' for temp, speed in points)
                                     + '  |  Sabit RPM değil; sıcaklığa göre donanım eğrisi.')

    def update_current_fan_curve(self, *args):
        channel = self.fan_channel.currentData()
        item = next((item for item in self.current_fan_channels if item['channel'] == channel), None)
        self.fan_curve_info.setText(hardware_fan_curve_text(item))

    def apply_fan_preset(self):
        key = self.preset_combo.currentData()
        points = preset_points(key)
        if points is None:
            self.fan_feedback.setText('Geçerli bir hazır fan eğrisi seçin.')
            return
        self.fan_action('curve', points, FAN_PRESETS[key][0])

    def fan_action(self, action, points=None, preset_name=None, expected_channel=None):
        helper = '/usr/libexec/anvil-fan-helper'
        channel = self.fan_channel.currentData()
        if expected_channel is not None and channel != expected_channel:
            self.fan_feedback.setText('Fan kanalı değişti; işlem iptal edildi. Eğriyi seçili kanal için yeniden açın.')
            return
        if channel not in [item['channel'] for item in channels()]:
            self.fan_feedback.setText('Seçili kanal güvenli fan kontrolü için uygun değil; arayüzü yeniden kontrol edin.')
            return
        if not Path(helper).exists():
            self.fan_feedback.setText('Fan yardımcısı için güncel Anvil RPM paketini kurun.')
            return
        if self.hardware_busy():
            return
        args = [helper, str(channel), action]
        if points is not None:
            args.append(json.dumps(points))
        self.fan_feedback.setText(f'Kanal {channel}: donanıma yazma ve geri okuma bekleniyor…')
        def done(ok, out, err):
            verified, message = fan_result(ok, out, err, action, channel)
            if verified and preset_name:
                message = f'{preset_name} eğrisi: {message}'
            message = f'Kanal {channel}: {message}'
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
                       'ram': percent(d['memory_used'], d['memory_total'])}
        for key, meter in self.meters.items():
            meter.set_value(percentages[key])
        vram = (f"{gpu['memory_used']/2**30:.1f} / {gpu['memory_total']/2**30:.1f} GiB"
                if gpu.get('memory_used') is not None and gpu.get('memory_total') else '—')
        disk_percent = percent(d['disk_used'], d['disk_total'])
        self.resources.setText(f"VRAM  {vram}     ·     Disk /  {fmt(disk_percent, ' %')} dolu")
        self.check_alerts(d)
        self.cards['cpu'].setText(fmt(d['cpu_temp'], ' °C'))
        self.cards['load'].setText(fmt(d['cpu_usage'], ' %'))
        self.cards['gpu'].setText(fmt(gpu.get('temperature'), ' °C'))
        ram_text = (f"{d['memory_used']/2**30:.1f} / {d['memory_total']/2**30:.1f} GiB"
                    if d['memory_used'] is not None and d['memory_total'] else '—')
        self.cards['ram'].setText(ram_text)
        self.update_chart()
        stamp = datetime.fromtimestamp(d['time']).strftime('%H:%M:%S')
        self.status.setText(f'●  CANLI   •   Son ölçüm {stamp}   •   {self.monitor.identity["os"]}')
        gpu_fan = (fmt(gpu.get('fan'), ' %') if gpu.get('fan') is not None
                   else fmt(gpu.get('fan_rpm'), ' RPM'))
        self.summary.setText(f"{gpu.get('name', 'GPU telemetrisi kullanılamıyor')}\n"
            f"GPU kullanımı {fmt(gpu.get('usage'), ' %')}   ·   Güç {fmt(gpu.get('power'), ' W', 1)}   ·   GPU fanı {gpu_fan}\n"
            f"CPU frekansı {fmt(d['cpu_mhz'], ' MHz')}   ·   Açık kalma {hours(d['uptime'])} saat   ·   Disk / {d['disk_used']/2**30:.0f} / {d['disk_total']/2**30:.0f} GB")
        self.render_sensors()
        fans = [s for s in d['sensors'] if s['unit'] == 'RPM']
        spinning = [s for s in fans if s['value'] > 0]
        self.gpu_fan.setText('GPU FAN  ' + gpu_fan)
        self.fan_readings.setText('  ·  '.join(f"{s['chip']} / {s['label']}: {s['value']:.0f} RPM" for s in spinning)
                                  or ('Algılanan fanların hiçbiri dönmüyor.' if fans else ''))
        self.fan_readings.setVisible(bool(fans))
        pwm = list(Path('/sys/class/hwmon').glob('hwmon*/pwm[0-9]'))
        self.monitor.identity['pwm'] = [str(p) for p in pwm]
        controllable = channels()
        available_channels = [item['channel'] for item in controllable]
        shown_channels = [self.fan_channel.itemData(i) for i in range(self.fan_channel.count())]
        selected = self.fan_channel.currentData()
        self.current_fan_channels = controllable
        if available_channels != shown_channels:
            with QSignalBlocker(self.fan_channel):
                self.fan_channel.clear()
                if available_channels:
                    for item in controllable:
                        self.fan_channel.addItem(fan_channel_label(item), item['channel'])
                    preferred = preferred_fan_channel(controllable, selected)
                    self.fan_channel.setCurrentIndex(available_channels.index(preferred))
                else:
                    self.fan_channel.addItem('Uygun kanal yok', None)
        else:
            for index, item in enumerate(controllable):
                self.fan_channel.setItemText(index, fan_channel_label(item))
        self.update_current_fan_curve()
        helper_installed = Path('/usr/libexec/anvil-fan-helper').exists()
        enabled = bool(controllable) and helper_installed and not self.hardware_busy()
        # Inspecting read-only hardware curves must not depend on write privileges.
        self.fan_channel.setEnabled(bool(controllable))
        for b in self.fan_controls:
            b.setEnabled(enabled)
        if not controllable and not self.monitor.identity['asus']:
            self.fan_feedback.setText('ASUS dışı sistemde fan izleme mümkündür; anakart fan yazımı kapalı.')
        elif not controllable and not supports_fan_write(self.monitor.identity['board'], self.monitor.identity['vendor']):
            self.fan_feedback.setText('Bu ASUS modelinde fan yazma profili henüz doğrulanmadı. Hız eğrilerini inceleyebilirsiniz; uygulama kapalı.')
        elif not controllable:
            self.fan_feedback.setText('Doğrulanmış kartta güvenli fan kanalı bulunamadı. Tek NCT6798, PWM/PECI ve donanım eğrisi geri okumalarını kontrol edin.')
        elif not helper_installed:
            self.fan_feedback.setText('Fan denetleyicisi bulundu. Kontrol için güncel RPM paketini kurun.')
        elif self.fan_feedback.text() == 'Kontrol desteği denetleniyor…':
            self.fan_feedback.setText('Otomatik eğri / tam hız hazır. Kanal numaraları fiziksel CPU/kasa etiketi değildir.')
        self.fan_status.setText(f'{len(spinning)} dönen fan / {len(fans)} devir sensörü • {len(pwm)} PWM arayüzü bulundu.' if fans or pwm
                               else 'Fan devir / PWM arayüzü görünmüyor. Mevcut kernel sürücülerinden fan kontrolü alınamıyor.')
        overview, capabilities = capability_report(self.monitor.identity, d, available_channels, helper_installed)
        self.compatibility.setText(overview)
        rows(self.capability_table, capabilities)
        names = {'power-saver':'Enerji tasarrufu', 'balanced':'Dengeli', 'performance':'Performans'}
        self.active_profile.setText('Etkin profil: ' + names.get(d['profile'], d['profile'] or 'Servise erişilemiyor'))
        available = [p.get('Profile', {}).get('data') for p in d['profiles']]
        for key, b in self.profile_buttons.items():
            b.setEnabled(key in available and not self.profile_pending)
            b.setChecked(key == d['profile'])
        self.diagnostics.setPlainText('\n\n'.join([
            'SICAKLIKLAR\n' + f"{len(d['sensors'])} sensör okunuyor.",
            'FAN KONTROLÜ\n' + self.fan_status.text() + '\n' + self.fan_feedback.text(),
            'GPU\n' + (gpu.get('name', '') + ' • ' + gpu.get('source', 'NVIDIA NVML') + ' ile okunuyor.'
                       if gpu else 'GPU telemetrisi alınamadı. Donanım ekranından sürücüyü inceleyin.'),
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
    app.setDesktopFileName('io.anvil.Control')
    app.setWindowIcon(QIcon.fromTheme('io.anvil.Control', QIcon.fromTheme('computer')))
    configure_style(app)
    window = Window()
    window.show()
    sys.exit(app.exec())
