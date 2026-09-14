#!/usr/bin/env python3
"""Build historical Sol-Ark energy totals from a SolarAssistant InfluxDB backup.

The SolarAssistant backup must first be restored to a temporary InfluxDB 1.8
database (see docs/solarassistant-energy-backfill.md). This tool reads the
hourly continuous-query measurements, produces an auditable CSV, and can write
daily/cumulative points to the project's InfluxDB 2 bucket.

Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import getpass
import json
from pathlib import Path
import sys
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


SERIES = {
    "pv": "PV power hourly",
    "load": "Load power hourly",
    "grid_import": "Grid power in hourly",
    "grid_export": "Grid power out hourly",
    "battery_charge": "Battery power in hourly",
    "battery_discharge": "Battery power out hourly",
}


@dataclass(frozen=True)
class Point:
    timestamp: datetime
    watt_hours: float


def _request(url: str, *, headers: dict[str, str] | None = None,
             data: bytes | None = None) -> bytes:
    request = Request(url, headers=headers or {}, data=data)
    try:
        with urlopen(request, timeout=60) as response:
            return response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Unable to reach {url}: {exc.reason}") from exc


def query_influx1(base_url: str, database: str, measurement: str) -> list[Point]:
    query = f'SELECT "combined" FROM "autogen"."{measurement}" ORDER BY time ASC'
    url = f"{base_url.rstrip('/')}/query?{urlencode({'db': database, 'q': query})}"
    payload = json.loads(_request(url))
    if payload.get("results", [{}])[0].get("error"):
        raise RuntimeError(payload["results"][0]["error"])
    series = payload.get("results", [{}])[0].get("series", [])
    if not series:
        return []
    columns = series[0]["columns"]
    time_index = columns.index("time")
    value_index = columns.index("combined")
    points = []
    for row in series[0].get("values", []):
        if row[value_index] is None:
            continue
        stamp = datetime.fromisoformat(row[time_index].replace("Z", "+00:00"))
        points.append(Point(stamp, float(row[value_index])))
    return points


def aggregate_daily(all_points: dict[str, list[Point]], tz: ZoneInfo) -> list[dict[str, object]]:
    daily: dict[object, dict[str, float]] = {}
    hourly_coverage: dict[object, set[datetime]] = {}
    for key, points in all_points.items():
        for point in points:
            day = point.timestamp.astimezone(tz).date()
            daily.setdefault(day, {name: 0.0 for name in SERIES})
            if key == "pv":
                hourly_coverage.setdefault(day, set()).add(point.timestamp)
            # SolarAssistant's hourly CQs integrate watts over the hour and
            # store watt-hours in the field named "combined".
            daily[day][key] += point.watt_hours / 1000.0

    running = {name: 0.0 for name in SERIES}
    rows: list[dict[str, object]] = []
    for day in sorted(daily):
        values = daily[day]
        for key in SERIES:
            running[key] += values[key]
        stamp = datetime.combine(day, time(23, 59, 59), tzinfo=tz)
        next_midnight = datetime.combine(day + timedelta(days=1), time(), tzinfo=tz)
        midnight = datetime.combine(day, time(), tzinfo=tz)
        expected_hours = int(
            (next_midnight.astimezone(timezone.utc) - midnight.astimezone(timezone.utc))
            .total_seconds() / 3600
        )
        hours_present = len(hourly_coverage.get(day, set()))
        row: dict[str, object] = {
            "date": day.isoformat(),
            "timestamp": stamp.isoformat(),
            "hours_present": hours_present,
            "expected_hours": expected_hours,
            "complete_day": hours_present == expected_hours,
        }
        row.update({f"daily_{k}_kwh": round(values[k], 6) for k in SERIES})
        row.update({f"total_{k}_kwh": round(running[k], 6) for k in SERIES})
        rows.append(row)
    return rows


def apply_anchors(rows: list[dict[str, object]], anchors: dict[str, float]) -> None:
    """Shift running totals so the last backup value equals a known live total."""
    if not rows:
        return
    last = rows[-1]
    for key, anchor in anchors.items():
        if key not in SERIES:
            raise ValueError(f"Unknown anchor {key!r}; expected one of {sorted(SERIES)}")
        field = f"total_{key}_kwh"
        offset = float(anchor) - float(last[field])
        for row in rows:
            row[field] = round(float(row[field]) + offset, 6)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError("No SolarAssistant energy data was found")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, object]]:
    """Read a previously validated backfill CSV for a write-only run."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows: list[dict[str, object]] = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"No rows found in {path}")
    required = {"date", "timestamp", *(f"daily_{key}_kwh" for key in SERIES),
                *(f"total_{key}_kwh" for key in SERIES)}
    missing = required - set(rows[0])
    if missing:
        raise RuntimeError("CSV is missing required columns: " + ", ".join(sorted(missing)))
    return rows


def line_protocol(rows: Iterable[dict[str, object]], source: str) -> bytes:
    lines = []
    for row in rows:
        timestamp = datetime.fromisoformat(str(row["timestamp"])).astimezone(timezone.utc)
        timestamp_ns = int(timestamp.timestamp() * 1_000_000_000)
        fields = []
        for key, value in row.items():
            if key.startswith(("daily_", "total_")):
                fields.append(f"{key}={float(value)!r}")
        lines.append(f"solark_energy_totals,source={source} {','.join(fields)} {timestamp_ns}")
    return "\n".join(lines).encode("utf-8")


def write_influx2(url: str, org: str, bucket: str, token: str, payload: bytes) -> None:
    endpoint = f"{url.rstrip('/')}/api/v2/write?{urlencode({'org': org, 'bucket': bucket, 'precision': 'ns'})}"
    _request(endpoint, headers={"Authorization": f"Token {token}",
                                "Content-Type": "text/plain; charset=utf-8"}, data=payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url", default="http://127.0.0.1:8086")
    parser.add_argument("--source-db", default="solar_assistant_restore")
    parser.add_argument("--timezone", default="America/New_York")
    parser.add_argument("--output", type=Path, default=Path("solarassistant_energy_totals.csv"))
    parser.add_argument("--input-csv", type=Path,
                        help="Write an existing validated CSV; skip the InfluxDB 1 restore query")
    parser.add_argument("--anchors", type=Path,
                        help="JSON object of final lifetime totals, in kWh")
    parser.add_argument("--write", action="store_true",
                        help="Write to InfluxDB 2 after creating the CSV")
    parser.add_argument("--influx2-url")
    parser.add_argument("--influx2-org")
    parser.add_argument("--influx2-bucket", default="solark")
    parser.add_argument("--influx2-token")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.input_csv:
            rows = read_csv(args.input_csv)
            if args.anchors:
                raise RuntimeError("--anchors cannot be combined with --input-csv; regenerate the CSV instead")
            print(f"Validated {len(rows)} daily rows from {args.input_csv}")
        else:
            tz = ZoneInfo(args.timezone)
            points = {key: query_influx1(args.source_url, args.source_db, measurement)
                      for key, measurement in SERIES.items()}
            missing = [SERIES[key] for key, values in points.items() if not values]
            if missing:
                raise RuntimeError("Missing restored measurements: " + ", ".join(missing))
            rows = aggregate_daily(points, tz)
            if args.anchors:
                apply_anchors(rows, json.loads(args.anchors.read_text(encoding="utf-8")))
            write_csv(args.output, rows)
            print(f"Wrote {len(rows)} daily rows to {args.output}")
        if args.write:
            if not args.influx2_url or not args.influx2_org:
                raise RuntimeError("--write requires --influx2-url and --influx2-org")
            token = args.influx2_token or getpass.getpass("InfluxDB write token: ")
            if not token:
                raise RuntimeError("An InfluxDB write token is required")
            payload = line_protocol(rows, "solarassistant_backfill")
            write_influx2(args.influx2_url, args.influx2_org,
                          args.influx2_bucket, token, payload)
            print(f"Wrote {len(rows)} duplicate-safe points to bucket {args.influx2_bucket}")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
