class ThermalAlerts:
    """One event per crossing; 5 °C hysteresis avoids notification chatter."""
    def __init__(self):
        self.active = set()

    def check(self, readings, threshold):
        events = []
        for key, value in readings.items():
            if value is None:
                continue
            if value >= threshold and key not in self.active:
                self.active.add(key)
                events.append(f'{key}: {value:.0f} °C — {threshold} °C uyarı eşiği aşıldı.')
            elif value <= threshold - 5:
                self.active.discard(key)
        return events


class SensorStats:
    def __init__(self):
        self.values = {}

    def add(self, sensors):
        for sensor in sensors:
            key = sensor['path']
            value = sensor['value']
            low, high = self.values.get(key, (value, value))
            self.values[key] = min(low, value), max(high, value)
