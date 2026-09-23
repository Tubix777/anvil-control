import os
import unittest
from collections import deque

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QPointF, QVariantAnimation
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from anvil.app import Chart, Motherboard, THEMES


class VisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_board_routes_and_theme_rendering(self):
        points = ((0, 0), (10, 0), (10, 10))
        self.assertEqual(Motherboard.trace_position(points, 0), QPointF(0, 0))
        self.assertEqual(Motherboard.trace_position(points, 0.5), QPointF(10, 0))
        board = Motherboard()
        board.set_motion(False)
        board.set_temperature(42)
        for theme in THEMES.values():
            board.theme = theme
            self.assertFalse(board.grab().isNull())
        self.assertIn('Temsili', board.toolTip())
        board.close()

    def test_board_and_chart_animations_stop_when_disabled_or_hidden(self):
        board = Motherboard()
        board.show()
        QTest.qWait(100)
        self.assertTrue(board.timer.isActive())
        self.assertGreater(board.phase, 0)
        board.set_motion(False)
        self.assertFalse(board.timer.isActive())
        board.set_temperature(45)
        self.assertNotEqual(board.animation.state(), QVariantAnimation.State.Running)
        board.set_motion(True)
        self.assertTrue(board.timer.isActive())
        board.hide()
        self.assertFalse(board.timer.isActive())

        chart = Chart()
        chart.values = deque([22, 37])
        chart.show()
        chart.pulse_latest()
        self.assertEqual(chart.animation.state(), QVariantAnimation.State.Running)
        chart.set_motion(False)
        self.assertEqual(chart.highlight, 0)
        self.assertNotEqual(chart.animation.state(), QVariantAnimation.State.Running)
        chart.close()
        board.close()


if __name__ == '__main__':
    unittest.main()
