"""Finite interaction animations, with no telemetry or hardware operations."""
import math

from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QLinearGradient
from PySide6.QtWidgets import QFrame, QPushButton


def tween(parent, duration, callback):
    animation = QVariantAnimation(parent)
    animation.setDuration(duration)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.valueChanged.connect(callback)
    return animation


class MotionButton(QPushButton):
    """Hover illumination and an expanding click ring; normal button semantics."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion = True
        self.accent_color = '#ffd438'
        self.hover_level = 0.0
        self.ripple = 1.0
        self.origin = None
        self.hover_animation = tween(self, 180, self._hover_frame)
        self.press_animation = tween(self, 420, self._press_frame)
        self.pressed.connect(self._press)

    def _hover_frame(self, value):
        self.hover_level = float(value)
        self.update()

    def _press_frame(self, value):
        self.ripple = float(value)
        self.update()

    def set_motion(self, enabled):
        self.motion = bool(enabled)
        if not enabled:
            self.stop_motion()

    def stop_motion(self):
        self.hover_animation.stop()
        self.press_animation.stop()
        self.hover_level, self.ripple = 0.0, 1.0
        self.update()

    def enterEvent(self, event):
        if self.motion and self.isEnabled():
            self._hover_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_to(0.0)
        super().leaveEvent(event)

    def _hover_to(self, target):
        self.hover_animation.stop()
        if self.motion and self.isVisible():
            self.hover_animation.setStartValue(self.hover_level)
            self.hover_animation.setEndValue(target)
            self.hover_animation.start()
        else:
            self._hover_frame(0.0)

    def mousePressEvent(self, event):
        self.origin = event.position()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        self.origin = None
        super().keyPressEvent(event)

    def _press(self):
        if not self.motion or not self.isVisible() or not self.isEnabled():
            return
        self.press_animation.stop()
        self.press_animation.setStartValue(0.0)
        self.press_animation.setEndValue(1.0)
        self.press_animation.start()

    def hideEvent(self, event):
        self.stop_motion()
        super().hideEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.isEnabled() or (self.hover_level == 0 and self.ripple >= 1):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 8, 8)
        painter.setClipPath(clip)
        color = QColor(self.accent_color)
        color.setAlpha(int(20 * self.hover_level))
        painter.fillPath(clip, color)
        if self.ripple < 1:
            center = self.origin or QPointF(rect.center())
            radius = math.hypot(self.width(), self.height()) * self.ripple
            color.setAlpha(int(95 * (1 - self.ripple)))
            painter.setPen(QPen(color, 2.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, radius, radius)
        painter.end()


class MotionCard(QFrame):
    """Theme-aware edge glow and a staggered, single-pass entrance glint."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion = True
        self.accent_color = '#ffd438'
        self.hover_level = 0.0
        self.reveal = 1.0
        self.hover_animation = tween(self, 220, self._hover_frame)
        self.reveal_animation = tween(self, 650, self._reveal_frame)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def _hover_frame(self, value):
        self.hover_level = float(value)
        self.update()

    def _reveal_frame(self, value):
        self.reveal = float(value)
        self.update()

    def set_motion(self, enabled):
        self.motion = bool(enabled)
        if not enabled:
            self.stop_motion()

    def stop_motion(self):
        self.hover_animation.stop()
        self.reveal_animation.stop()
        self.hover_level, self.reveal = 0.0, 1.0
        self.update()

    def animate_in(self, order=0):
        self.reveal_animation.stop()
        if self.motion and self.isVisible():
            # Negative progress provides a stagger without queued timer callbacks.
            self.reveal_animation.setStartValue(-min(order, 7) * .16)
            self.reveal_animation.setEndValue(1.0)
            self.reveal_animation.start()
        else:
            self._reveal_frame(1.0)

    def enterEvent(self, event):
        self._hover_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_to(0.0)
        super().leaveEvent(event)

    def _hover_to(self, target):
        self.hover_animation.stop()
        if self.motion and self.isVisible():
            self.hover_animation.setStartValue(self.hover_level)
            self.hover_animation.setEndValue(target)
            self.hover_animation.start()
        else:
            self._hover_frame(0.0)

    def hideEvent(self, event):
        self.stop_motion()
        super().hideEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.hover_level and not 0 < self.reveal < 1:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 13, 13)
        color = QColor(self.accent_color)
        color.setAlpha(int(110 * self.hover_level))
        painter.setPen(QPen(color, 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        if 0 < self.reveal < 1:
            painter.setClipPath(path)
            x = -self.width() * .4 + self.width() * 1.8 * self.reveal
            gradient = QLinearGradient(x - 100, 0, x + 100, self.height())
            transparent = QColor(self.accent_color)
            transparent.setAlpha(0)
            bright = QColor(self.accent_color)
            bright.setAlpha(int(32 * math.sin(math.pi * self.reveal)))
            gradient.setColorAt(0, transparent)
            gradient.setColorAt(.5, bright)
            gradient.setColorAt(1, transparent)
            painter.fillPath(path, gradient)
        painter.end()
