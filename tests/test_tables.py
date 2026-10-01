"""Table refresh regressions: live changes, filtering and stable selection."""
import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication
from anvil.app import rows, table


class TableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.widget = table(['Sensor', 'Value'])
        self.addCleanup(self.widget.close)

    def test_unchanged_refresh_preserves_cells_and_selection_without_notifications(self):
        data = [('CPU', 42), ('Fan', 900)]
        rows(self.widget, data)
        cell = self.widget.item(1, 1)
        self.widget.setCurrentCell(1, 1)
        self.widget.selectRow(1)
        changes = QSignalSpy(self.widget.model().dataChanged)
        rows(self.widget, data)
        self.assertEqual(changes.count(), 0)
        self.assertIs(self.widget.item(1, 1), cell)
        self.assertTrue(cell.isSelected())
        self.assertEqual(self.widget.currentRow(), 1)

    def test_only_changed_value_notifies_and_reuses_cell(self):
        rows(self.widget, [('Fan', 900)])
        cell = self.widget.item(0, 1)
        changes = QSignalSpy(self.widget.model().dataChanged)
        rows(self.widget, [('Fan', 1200)])
        self.assertIs(self.widget.item(0, 1), cell)
        self.assertEqual(cell.text(), '1200')
        self.assertEqual(changes.count(), 1)

    def test_filter_clear_and_new_sensors_leave_no_old_readings(self):
        for data in [[('CPU', 42), ('Fan', 900)], [('Fan', 950)], [],
                     [('NVMe', 36), ('CPU', 45), ('Fan', 1000)]]:
            with self.subTest(data=data):
                rows(self.widget, data)
                self.assertEqual(self.widget.rowCount(), len(data))
                self.assertEqual([[self.widget.item(i, j).text() for j in range(2)]
                                  for i in range(len(data))],
                                 [[str(value) for value in row] for row in data])
