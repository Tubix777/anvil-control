"""Lightweight Qt animations. No polling or hardware access in paint code."""
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class Meter(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(7)
        self.value = 0.0
        self.available = False
        self.motion = True
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(550)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self.advance)

    def advance(self, value):
        self.value = float(value)
        self.update()

    def set_value(self, value):
        self.animation.stop()
        self.available = value is not None
        target = max(0, min(100, value)) if value is not None else 0
        if self.motion and self.isVisible():
            self.animation.setStartValue(self.value)
            self.animation.setEndValue(float(target))
            self.animation.start()
        else:
            self.advance(target)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#343127'))
        p.drawRoundedRect(QRectF(self.rect()), 3, 3)
        if self.available:
            p.setBrush(QColor('#ffd438'))
            p.drawRoundedRect(QRectF(0, 0, self.width()*self.value/100, 7), 3, 3)
        p.end()


class FanRotor(QWidget):
    """Visual motion indicates reported GPU fan activity, not actual RPM."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(38, 38)
        self.speed = None
        self.angle = 0
        self.motion = True
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.tick)
        self.setToolTip('GPU fan etkinliği; animasyon gerçek devir hızını göstermez.')

    def set_speed(self, speed):
        self.speed = speed
        self.sync()
        self.update()

    def sync(self):
        if self.motion and self.speed is not None and self.speed > 0 and self.isVisible():
            self.timer.start()
        else:
            self.timer.stop()

    def showEvent(self, event):
        self.sync()

    def hideEvent(self, event):
        self.timer.stop()

    def tick(self):
        self.angle = (self.angle + 4 + min(self.speed or 0, 100)/10) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(19, 19)
        p.setPen(QPen(QColor('#615a38'), 1))
        p.drawEllipse(QRectF(-17, -17, 34, 34))
        p.rotate(self.angle)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#ffd438' if self.speed is not None else '#777264'))
        for _ in range(4):
            p.drawRoundedRect(QRectF(2, -5, 12, 7), 3, 3)
            p.rotate(90)
        p.drawEllipse(QRectF(-4, -4, 8, 8))
        p.end()
