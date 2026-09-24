"""Short-lived, read-only RPM observations for the selected fan channel.

This module never talks to hardware or writes observations to disk. It only
summarizes the channel readbacks already collected by :mod:`anvil.fans`.
"""

from collections import deque
from math import isfinite


def _nonnegative_number(value):
    if type(value) not in (int, float):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if isfinite(number) and number >= 0 else None


def _channel_number(value):
    return value if type(value) is int and value > 0 else None


def _display_number(value):
    """Keep integer sysfs readings exact while allowing fractional test data."""
    return f'{value:.0f}' if value.is_integer() else f'{value:.1f}'.rstrip('0').rstrip('.').replace('.', ',')


class FanRpmHistory:
    """Keep a bounded, per-channel window of available RPM readbacks."""

    def __init__(self, window_seconds=60.0, max_samples=120):
        window = _nonnegative_number(window_seconds)
        if window is None or window == 0:
            raise ValueError('window_seconds must be finite and positive')
        if type(max_samples) is not int or max_samples < 1:
            raise ValueError('max_samples must be a positive integer')
        self.window_seconds = window
        self.max_samples = max_samples
        self._samples = {}
        self._last_timestamp = None

    def clear(self) -> None:
        """Discard a trend after sampling is interrupted."""
        self._samples.clear()
        self._last_timestamp = None

    def record(self, timestamp: float, channels: list[dict]) -> None:
        """Store readbacks once per timestamp; unavailable channels lose history."""
        now = _nonnegative_number(timestamp)
        if now is None:
            return
        if self._last_timestamp is not None and now < self._last_timestamp:
            # Wall-clock corrections make elapsed-time comparisons meaningless.
            self._samples.clear()
        self._last_timestamp = now

        current = {}
        seen = set()
        ambiguous = set()
        for item in channels if isinstance(channels, list) else ():
            if not isinstance(item, dict):
                continue
            channel = _channel_number(item.get('channel'))
            if channel is None:
                continue
            if channel in seen:
                ambiguous.add(channel)
            seen.add(channel)
            rpm = _nonnegative_number(item.get('rpm'))
            if rpm is not None:
                current[channel] = rpm
        for channel in ambiguous:
            current.pop(channel, None)

        for channel in tuple(self._samples):
            if channel not in current:
                del self._samples[channel]
        cutoff = now - self.window_seconds
        for channel, rpm in current.items():
            samples = self._samples.setdefault(channel, deque(maxlen=self.max_samples))
            while samples and samples[0][0] < cutoff:
                samples.popleft()
            if samples and samples[-1][0] == now:
                samples[-1] = (now, rpm)
            else:
                samples.append((now, rpm))

    def summary(self, channel: int | None) -> str:
        """Describe observations without inferring cause or control state."""
        channel = _channel_number(channel)
        if channel is None:
            return 'Devir geçmişi için fan kanalı seçin.'
        samples = self._samples.get(channel)
        if not samples:
            return f'Kanal {channel} · Devir geçmişi henüz yok.'

        window = _display_number(self.window_seconds)
        rpms = [rpm for _, rpm in samples]
        count = len(samples)
        if count == 1:
            return (f'Kanal {channel} · Son {window} sn: 1 ölçüm · '
                    f'{_display_number(rpms[0])} RPM · Değişim için yeni ölçüm bekleniyor.')

        previous_time, previous_rpm = samples[-2]
        current_time, current_rpm = samples[-1]
        delta = current_rpm - previous_rpm
        sign = '+' if delta >= 0 else '−'
        return (f'Kanal {channel} · Son {window} sn: {count} ölçüm · '
                f'{_display_number(min(rpms))}–{_display_number(max(rpms))} RPM · '
                f'Son değişim {sign}{_display_number(abs(delta))} RPM / '
                f'{_display_number(current_time - previous_time)} sn.')
