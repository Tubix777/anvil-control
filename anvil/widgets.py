"""Lightweight Qt animations. No polling or hardware access in paint code."""
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import QWidget


class Meter(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(7)
        self.value = 0.0
        self.available = False
        self.motion = True
        self.track_color = '#343127'
        self.accent_color = '#ffd438'
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
        p.setBrush(QColor(self.track_color))
        p.drawRoundedRect(QRectF(self.rect()), 3, 3)
        if self.available:
            p.setBrush(QColor(self.accent_color))
            p.drawRoundedRect(QRectF(0, 0, self.width()*self.value/100, 7), 3, 3)
        p.end()


class FanRotor(QWidget):
    """Visual motion indicates reported GPU fan activity, not actual RPM."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(50, 50)
        self.setAccessibleName('GPU fan etkinliği — temsili animasyon')
        self.speed = None
        self.angle = 0
        self.motion = True
        self.ring_color = '#615a38'
        self.accent_color = '#ffd438'
        self.disabled_color = '#777264'
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
        p.translate(25, 25)
        p.setPen(QPen(QColor(self.ring_color), 1))
        p.drawEllipse(QRectF(-23, -23, 46, 46))
        p.drawEllipse(QRectF(-20, -20, 40, 40))
        if self.speed is not None and self.speed > 0:
            rim = QColor(self.accent_color)
            rim.setAlpha(150)
            p.setPen(QPen(rim, 2.1))
            p.drawArc(QRectF(-23, -23, 46, 46), int(-self.angle * 16), 100 * 16)
        p.rotate(self.angle)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.accent_color if self.speed is not None else self.disabled_color))
        blade = QPainterPath()
        blade.moveTo(3, -2)
        blade.cubicTo(7, -14, 18, -19, 18, -7)
        blade.cubicTo(14, 0, 8, 4, 3, -2)
        for _ in range(5):
            p.drawPath(blade)
            p.rotate(72)
        p.drawEllipse(QRectF(-4, -4, 8, 8))
        p.end()
