"""Tests for dependency-free InfluxDB fast-path serialization."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from module_loader import load_integration_module

line_protocol = load_integration_module("influx_line_protocol")


class InfluxLineProtocolTests(unittest.TestCase):
    """Ensure valid numeric values are serialized and unsafe values are ignored."""

    def test_numeric_event_is_escaped_and_serialized(self) -> None:
        event = {
            "measurement": "Waveshare power,total",
            "tags": {"entity id": "sensor.sol_ark=15k,1"},
            "fields": {"value": 6335},
            "time": datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
        }
        self.assertEqual(
            line_protocol.event_json_to_line(event),
            "Waveshare\\ power\\,total,entity\\ id=sensor.sol_ark\\=15k\\,1 "
            "value=6335.0 1789819200000000000",
        )

    def test_non_numeric_and_non_finite_values_are_ignored(self) -> None:
        for value in (True, "12", float("nan"), float("inf"), None):
            with self.subTest(value=value):
                self.assertIsNone(
                    line_protocol.event_json_to_line(
                        {"measurement": "sensor", "fields": {"value": value}}
                    )
                )

    def test_filtered_or_malformed_event_is_ignored(self) -> None:
        self.assertIsNone(line_protocol.event_json_to_line(None))
        self.assertIsNone(line_protocol.event_json_to_line({}))
        self.assertIsNone(
            line_protocol.event_json_to_line(
                {"measurement": "sensor", "fields": {"value": 1}, "tags": []}
            )
        )


if __name__ == "__main__":
    unittest.main()
