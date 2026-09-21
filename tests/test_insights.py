import unittest
from anvil.insights import ThermalAlerts, SensorStats


class InsightsTests(unittest.TestCase):
    def test_alert_hysteresis(self):
        alerts = ThermalAlerts()
        self.assertEqual(len(alerts.check({'CPU': 85}, 85)), 1)
        self.assertEqual(alerts.check({'CPU': 90}, 85), [])
        self.assertEqual(alerts.check({'CPU': 82}, 85), [])
        self.assertEqual(alerts.check({'CPU': 86}, 85), [])
        alerts.check({'CPU': 80}, 85)
        self.assertEqual(len(alerts.check({'CPU': 85}, 85)), 1)

    def test_missing_reading_does_not_clear_alert(self):
        alerts = ThermalAlerts()
        alerts.check({'GPU': 90}, 85)
        self.assertEqual(alerts.check({'GPU': None}, 85), [])
        self.assertIn('GPU', alerts.active)

    def test_independent_sources(self):
        alerts = ThermalAlerts()
        self.assertEqual(len(alerts.check({'CPU': 90, 'GPU': 90}, 85)), 2)
        alerts.check({'CPU': 30, 'GPU': 90}, 85)
        self.assertEqual(alerts.active, {'GPU'})

    def test_sensor_extrema(self):
        stats = SensorStats()
        for value in [40, 55, 32, 44]:
            stats.add([{'path':'sensor/a', 'value':value}])
        stats.add([{'path':'sensor/b', 'value':0}])
        self.assertEqual(stats.values['sensor/a'], (32, 55))
        self.assertEqual(stats.values['sensor/b'], (0, 0))
