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
        self.assertEqual(manifest["version"], "1.1.0rc1")
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

    def test_development_integration_has_guarded_fc16_path(self) -> None:
        integration = ROOT / "custom_components/solark15k"
        source = "\n".join(path.read_text() for path in integration.glob("*.py"))
        self.assertIn("FC_WRITE_MULTIPLE", source)
        self.assertIn("async_write_holding_one", source)
        self.assertTrue((ROOT / "tools/solark_tou_research.py").exists())
        self.assertTrue((integration / "number.py").exists())
        self.assertTrue((integration / "switch.py").exists())
        self.assertFalse((integration / "time.py").exists())
        self.assertIn("_remove_obsolete_tou_time_entities", source)
        self.assertIn("_migrate_control_entity_ids", source)

    def test_writes_require_explicit_opt_in(self) -> None:
        const_source = (ROOT / "custom_components/solark15k/const.py").read_text()
        setup_source = (ROOT / "custom_components/solark15k/__init__.py").read_text()
        flow_source = (ROOT / "custom_components/solark15k/config_flow.py").read_text()
        self.assertIn('DEFAULT_ACCESS_MODE = ACCESS_MODE_READ_ONLY', const_source)
        self.assertIn('ACCESS_MODE_READ_WRITE', setup_source)
        self.assertIn('READ_ONLY_PLATFORMS', setup_source)
        self.assertIn('NumberSelectorMode.BOX', flow_source)

    def test_x2_is_anchored_to_master_entry(self) -> None:
        source = (ROOT / "custom_components/solark15k/system_sensor.py").read_text()
        self.assertIn("MASTER_SLAVE_ID", source)
        self.assertIn("master_add_entities", source)
        self.assertIn("remove_config_entry_id", source)

    def test_release_contains_four_supported_dashboards(self) -> None:
        dashboards = sorted((ROOT / "grafana/dashboards").glob("*.json"))
        self.assertEqual(len(dashboards), 4)


if __name__ == "__main__":
    unittest.main()
