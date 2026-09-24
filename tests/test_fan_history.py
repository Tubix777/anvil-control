"""Pure RPM-history tests: no hardware access or privileged helper calls."""

import unittest

from anvil.fan_history import FanRpmHistory


def fan(channel, rpm):
    return {'channel': channel, 'rpm': rpm}


class FanRpmHistoryTests(unittest.TestCase):
    def test_channels_are_separate_and_latest_delta_is_factual(self):
        history = FanRpmHistory()
        history.record(10, [fan(1, 500), fan(2, 1300)])
        history.record(12, [fan(1, 900), fan(2, 1000)])
        first = history.summary(1)
        second = history.summary(2)
        self.assertIn('Kanal 1 · Son 60 sn: 2 ölçüm', first)
        self.assertIn('500–900 RPM', first)
        self.assertIn('Son değişim +400 RPM / 2 sn', first)
        self.assertIn('1000–1300 RPM', second)
        self.assertIn('Son değişim −300 RPM / 2 sn', second)
        self.assertNotIn('1300', first)

    def test_duplicate_timestamp_replaces_last_readback(self):
        history = FanRpmHistory()
        history.record(10, [fan(1, 500)])
        history.record(10, [fan(1, 700)])
        self.assertIn('1 ölçüm · 700 RPM', history.summary(1))
        history.record(12, [fan(1, 800)])
        self.assertIn('Son değişim +100 RPM / 2 sn', history.summary(1))

    def test_unavailable_or_unreadable_channel_discards_stale_history(self):
        history = FanRpmHistory()
        history.record(10, [fan(1, 500), fan(2, 1300)])
        history.record(11, [fan(1, float('nan')), fan(2, 1200)])
        self.assertIn('henüz yok', history.summary(1))
        self.assertIn('2 ölçüm', history.summary(2))
        history.record(12, [])
        self.assertIn('henüz yok', history.summary(2))

    def test_invalid_rpm_and_ambiguous_channel_are_not_retained(self):
        for bad_rpm in (True, -1, float('inf'), float('-inf'), '500', None):
            with self.subTest(rpm=bad_rpm):
                history = FanRpmHistory()
                history.record(1, [fan(1, 500)])
                history.record(2, [fan(1, bad_rpm)])
                self.assertIn('henüz yok', history.summary(1))
        history = FanRpmHistory()
        history.record(1, [fan(1, 500)])
        history.record(2, [fan(1, 600), fan(1, 700)])
        self.assertIn('henüz yok', history.summary(1))
        history.record(3, [fan(1, None), fan(1, 800)])
        self.assertIn('henüz yok', history.summary(1))
        history.record(4, [fan(True, 500), fan(-1, 800)])
        self.assertIn('henüz yok', history.summary(1))

    def test_window_and_count_are_bounded(self):
        history = FanRpmHistory(window_seconds=5, max_samples=2)
        for timestamp, rpm in ((0, 100), (3, 200), (6, 300), (7, 400)):
            history.record(timestamp, [fan(1, rpm)])
        self.assertIn('Son 5 sn: 2 ölçüm', history.summary(1))
        self.assertIn('300–400 RPM', history.summary(1))
        history.record(20, [fan(1, 500)])
        self.assertIn('1 ölçüm · 500 RPM', history.summary(1))

    def test_backwards_clock_resets_elapsed_comparison(self):
        history = FanRpmHistory()
        history.record(20, [fan(1, 500)])
        history.record(21, [fan(1, 600)])
        history.record(19, [fan(1, 700)])
        self.assertIn('1 ölçüm · 700 RPM', history.summary(1))

    def test_sampling_interruption_discards_previous_comparison(self):
        history = FanRpmHistory()
        history.record(10, [fan(1, 500)])
        history.record(12, [fan(1, 900)])
        history.clear()
        self.assertIn('henüz yok', history.summary(1))
        history.record(14, [fan(1, 950)])
        self.assertIn('1 ölçüm · 950 RPM', history.summary(1))
        self.assertNotIn('Son değişim', history.summary(1))

    def test_invalid_timestamp_is_ignored(self):
        history = FanRpmHistory()
        history.record(10, [fan(1, 500)])
        for timestamp in (True, -1, float('nan'), float('inf'), '11'):
            history.record(timestamp, [fan(1, 800)])
        self.assertIn('1 ölçüm · 500 RPM', history.summary(1))

    def test_empty_selection_and_invalid_configuration(self):
        history = FanRpmHistory()
        self.assertIn('fan kanalı seçin', history.summary(None))
        self.assertIn('henüz yok', history.summary(1))
        for window, count in ((0, 2), (-1, 2), (float('inf'), 2), (True, 2), (60, 0), (60, True)):
            with self.subTest(window=window, count=count), self.assertRaises(ValueError):
                FanRpmHistory(window, count)


if __name__ == '__main__':
    unittest.main()
