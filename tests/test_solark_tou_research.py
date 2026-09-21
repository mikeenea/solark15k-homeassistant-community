import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "tools" / "solark_tou_research.py"
SPEC = importlib.util.spec_from_file_location("solark_tou_research", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TOUResearchTests(unittest.TestCase):
    def test_changed_registers_reports_only_common_changes(self):
        before = {100: 1, 101: 2, 102: 3}
        after = {100: 1, 101: 7, 103: 9}
        self.assertEqual(MODULE.changed_registers(before, after), [(101, 2, 7)])

    def test_snapshot_round_trip(self):
        document = MODULE.snapshot_document(
            "192.0.2.241", 502, 10, 11, {10: 5, 11: 9}
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            self.assertEqual(MODULE.load_snapshot(path), {10: 5, 11: 9})

    def test_write_confirmation_phrase_is_address_specific(self):
        args = MODULE.build_parser().parse_args(
            [
                "write-single",
                "192.0.2.241",
                "--address",
                "999",
                "--expected",
                "123",
                "--value",
                "124",
                "--confirm",
                "wrong",
            ]
        )
        with patch.dict(
            os.environ, {MODULE.WRITE_ENV_NAME: MODULE.WRITE_ENV_VALUE}, clear=False
        ):
            with self.assertRaisesRegex(RuntimeError, "--confirm must be exactly"):
                MODULE.run_write(args)

    def test_read_range_retries_after_transaction_failure(self):
        class FakeClient:
            def __init__(self):
                self.calls = 0
                self.closes = 0

            def read_holding(self, start, count):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("Transaction ID mismatch")
                return list(range(count))

            def close(self):
                self.closes += 1

        client = FakeClient()
        result = MODULE.read_range(client, 10, 11, 2, 0, 1)
        self.assertEqual(result, {10: 0, 11: 1})
        self.assertEqual(client.calls, 2)
        self.assertEqual(client.closes, 1)

    def test_fc16_confirmation_phrase_is_function_specific(self):
        args = MODULE.build_parser().parse_args(
            [
                "write-one-fc16",
                "192.0.2.241",
                "--address",
                "250",
                "--expected",
                "0",
                "--value",
                "30",
                "--confirm",
                "WRITE-MASTER-250-FROM-0-TO-30",
            ]
        )
        with patch.dict(
            os.environ, {MODULE.WRITE_ENV_NAME: MODULE.WRITE_ENV_VALUE}, clear=False
        ):
            with self.assertRaisesRegex(RuntimeError, "WRITE-FC16-MASTER"):
                MODULE.run_write_fc16(args)


if __name__ == "__main__":
    unittest.main()
