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


if __name__ == "__main__":
    unittest.main()
