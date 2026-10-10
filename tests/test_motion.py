"""Animation lifecycle and input semantics; never change system hardware."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QPoint, QSettings, Qt, QAbstractAnimation
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from anvil.app import Window
from anvil.motion import MotionButton, MotionCard


class MotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_mouse_and_keyboard_clicks_emit_exactly_once(self):
        button = MotionButton('Test')
        calls = []
        button.clicked.connect(lambda: calls.append(True))
        button.show()
        QTest.qWait(10)
        try:
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            self.assertEqual(len(calls), 1)
            self.assertEqual(button.press_animation.state(), QAbstractAnimation.State.Running)
            QTest.keyClick(button, Qt.Key.Key_Space)
            self.assertEqual(len(calls), 2)
            button.setEnabled(False)
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            self.assertEqual(len(calls), 2)
            button.set_motion(False)
            self.assertEqual(button.press_animation.state(), QAbstractAnimation.State.Stopped)
        finally:
            button.close()

    def test_hide_and_reduced_motion_finish_card_effects(self):
        host = QWidget()
        layout = QVBoxLayout(host)
        card = MotionCard()
        layout.addWidget(card)
        host.show()
        QTest.qWait(10)
        try:
            card.animate_in(3)
            card._hover_to(1)
            self.assertEqual(card.reveal_animation.state(), QAbstractAnimation.State.Running)
            card.set_motion(False)
            self.assertEqual(card.reveal, 1)
            self.assertEqual(card.hover_level, 0)
            self.assertEqual(card.reveal_animation.state(), QAbstractAnimation.State.Stopped)
            card.set_motion(True)
            card.animate_in()
            host.hide()
            self.assertEqual(card.reveal_animation.state(), QAbstractAnimation.State.Stopped)
        finally:
            host.close()

    def test_rapid_navigation_and_hide_restore_layout_and_opacity(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'test.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                window.show()
                for index in (1, 3, 0, 4, 2, 0):
                    window.navigate(index)
                    QTest.qWait(20)
                QTest.qWait(700)
                self.assertEqual(window.stack.currentWidget().pos(), QPoint(0, 0))
                self.assertEqual(window.fade_effect.opacity(), 1)
                self.assertEqual(window.page_slide.state(), QAbstractAnimation.State.Stopped)
                window.navigate(1)
                window.set_motion(False)
                self.assertEqual(window.stack.currentWidget().pos(), QPoint(0, 0))
                self.assertEqual(window.fade_effect.opacity(), 1)
                window.set_motion(True)
                window.navigate(0)
                window.hide()
                self.assertEqual(window.page_slide.state(), QAbstractAnimation.State.Stopped)
                self.assertFalse(window.board.timer.isActive())
                for control in window.findChildren(MotionButton):
                    self.assertEqual(control.press_animation.state(), QAbstractAnimation.State.Stopped)
            finally:
                window.quit_app()

    def test_animation_frames_never_trigger_fan_profile_or_rgb_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / 'test.ini'), QSettings.Format.IniFormat)
            with patch('anvil.app.QSettings', return_value=settings), patch.object(Window, 'refresh'):
                window = Window()
            try:
                with (patch.object(window, 'run_hardware') as hardware,
                      patch('anvil.app.ProfileWorker') as power,
                      patch('anvil.app.QProcess.startDetached') as external):
                    window.show()
                    for index in range(window.stack.count()):
                        window.navigate(index)
                        QTest.qWait(15)
                    window.apply_theme('daylight', persist=False)
                    QTest.qWait(800)
                    hardware.assert_not_called()
                    power.assert_not_called()
                    external.assert_not_called()
            finally:
                window.quit_app()
