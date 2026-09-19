"""Dependency-free helpers for the optional InfluxDB fast path."""

from __future__ import annotations

from datetime import datetime
import math
import time


def escape_measurement(value: str) -> str:
    """Escape an InfluxDB line-protocol measurement."""
    return value.replace("\\", "\\\\").replace(",", "\\,").replace(" ", "\\ ")


def escape_tag(value: str) -> str:
    """Escape an InfluxDB line-protocol tag key or value."""
    return (
        value.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace("=", "\\=")
        .replace(" ", "\\ ")
    )


def timestamp_ns(value: object) -> int:
    """Convert an event datetime to InfluxDB nanoseconds."""
    if isinstance(value, datetime):
        return int(value.timestamp() * 1_000_000_000)
    return time.time_ns()


def event_json_to_line(event_json: object) -> str | None:
    """Convert one numeric Home Assistant Influx event dictionary to a line."""
    if not isinstance(event_json, dict):
        return None
    fields = event_json.get("fields", {})
    if not isinstance(fields, dict):
        return None
    value = fields.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        return None
    measurement = event_json.get("measurement")
    if not measurement:
        return None
    tags = event_json.get("tags", {})
    if not isinstance(tags, dict):
        return None
    tag_text = "".join(
        f",{escape_tag(str(key))}={escape_tag(str(tag_value))}"
        for key, tag_value in sorted(tags.items())
    )
    timestamp = timestamp_ns(event_json.get("time"))
    return (
        f"{escape_measurement(str(measurement))}{tag_text} "
        f"value={numeric_value!r} {timestamp}"
    )
