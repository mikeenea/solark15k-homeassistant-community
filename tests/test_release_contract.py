"""Stable-release metadata and packaging contract tests."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseContractTests(unittest.TestCase):
    """Protect the HACS package and read-only stable boundary."""

    def test_manifest_metadata(self) -> None:
        manifest = json.loads(
            (ROOT / "custom_components/solark15k/manifest.json").read_text()
        )
        self.assertEqual(manifest["domain"], "solark15k")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertTrue(manifest["config_flow"])
        self.assertEqual(manifest["iot_class"], "local_polling")
        self.assertTrue(manifest["documentation"].startswith("https://github.com/"))

    def test_hacs_metadata_and_required_files(self) -> None:
        hacs = json.loads((ROOT / "hacs.json").read_text())
        self.assertEqual(hacs["name"], "Sol-Ark 15K Modbus")
        for relative in (
            "custom_components/solark15k/__init__.py",
            "custom_components/solark15k/config_flow.py",
            "custom_components/solark15k/manifest.json",
            "custom_components/solark15k/sensor.py",
            "custom_components/solark15k/strings.json",
            "docs/release-candidate-checklist.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_stable_integration_has_no_modbus_write_path(self) -> None:
        integration = ROOT / "custom_components/solark15k"
        source = "\n".join(path.read_text() for path in integration.glob("*.py"))
        self.assertNotIn("FC_WRITE", source)
        self.assertNotIn("write_single", source)
        self.assertFalse((ROOT / "tools/solark_tou_research.py").exists())

    def test_release_contains_four_supported_dashboards(self) -> None:
        dashboards = sorted((ROOT / "grafana/dashboards").glob("*.json"))
        self.assertEqual(len(dashboards), 4)


if __name__ == "__main__":
    unittest.main()
