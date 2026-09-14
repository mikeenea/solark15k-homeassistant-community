from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


MODULE = Path(__file__).parents[1] / "tools" / "solarassistant_energy_backfill.py"
SPEC = importlib.util.spec_from_file_location("backfill", MODULE)
backfill = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = backfill
SPEC.loader.exec_module(backfill)


class BackfillTests(unittest.TestCase):
    def test_daily_aggregation_and_running_totals(self):
        points = {
            key: [backfill.Point(datetime(2026, 1, 1, 12, tzinfo=timezone.utc), 1000.0)]
            for key in backfill.SERIES
        }
        rows = backfill.aggregate_daily(points, backfill.ZoneInfo("America/New_York"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["daily_pv_kwh"], 1.0)
        self.assertEqual(rows[0]["total_pv_kwh"], 1.0)
        self.assertEqual(rows[0]["hours_present"], 1)
        self.assertFalse(rows[0]["complete_day"])

    def test_csv_round_trip_for_write_only_mode(self):
        row = {"date": "2026-01-01", "timestamp": "2026-01-01T23:59:59-05:00"}
        row.update({f"daily_{key}_kwh": 1.0 for key in backfill.SERIES})
        row.update({f"total_{key}_kwh": 1.0 for key in backfill.SERIES})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "totals.csv"
            backfill.write_csv(path, [row])
            loaded = backfill.read_csv(path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["date"], "2026-01-01")

    def test_anchor_aligns_final_total_without_changing_daily(self):
        points = {
            key: [
                backfill.Point(datetime(2026, 1, 1, 12, tzinfo=timezone.utc), 1000.0),
                backfill.Point(datetime(2026, 1, 2, 12, tzinfo=timezone.utc), 2000.0),
            ]
            for key in backfill.SERIES
        }
        rows = backfill.aggregate_daily(points, backfill.ZoneInfo("America/New_York"))
        backfill.apply_anchors(rows, {"pv": 103.0})
        self.assertEqual(rows[-1]["total_pv_kwh"], 103.0)
        self.assertEqual(rows[0]["total_pv_kwh"], 101.0)
        self.assertEqual(rows[0]["daily_pv_kwh"], 1.0)


if __name__ == "__main__":
    unittest.main()
