#!/usr/bin/env python3
"""Validate the supported Grafana dashboard exports."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


DASHBOARD_DIR = Path("grafana/dashboards")
VARIABLE_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)")


def _panels(dashboard: dict) -> list[dict]:
    """Return top-level panels; supported dashboards do not use nested rows."""
    return list(dashboard.get("panels", []))


def _validate_layout(path: Path, panels: list[dict]) -> list[str]:
    errors: list[str] = []
    ids: set[int] = set()
    occupied: dict[tuple[int, int], int] = {}

    for panel in panels:
        panel_id = panel.get("id")
        title = panel.get("title", f"panel {panel_id}")
        if not isinstance(panel_id, int):
            errors.append(f"{path}: {title!r} has no integer panel id")
            continue
        if panel_id in ids:
            errors.append(f"{path}: duplicate panel id {panel_id}")
        ids.add(panel_id)

        pos = panel.get("gridPos")
        if not isinstance(pos, dict):
            errors.append(f"{path}: panel {panel_id} has no gridPos")
            continue
        x, y, width, height = (pos.get(key) for key in ("x", "y", "w", "h"))
        if not all(isinstance(value, int) for value in (x, y, width, height)):
            errors.append(f"{path}: panel {panel_id} has a non-integer grid position")
            continue
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 24:
            errors.append(f"{path}: panel {panel_id} has invalid grid position {pos}")
            continue

        for column in range(x, x + width):
            for row in range(y, y + height):
                cell = (column, row)
                if cell in occupied:
                    errors.append(
                        f"{path}: panels {occupied[cell]} and {panel_id} overlap at {cell}"
                    )
                    break
                occupied[cell] = panel_id
            else:
                continue
            break

    return errors


def _validate_variables(path: Path, dashboard: dict, raw_text: str) -> list[str]:
    defined = {
        item.get("name")
        for item in dashboard.get("templating", {}).get("list", [])
        if item.get("name")
    }
    defined.update(
        item.get("name")
        for item in dashboard.get("__inputs", [])
        if item.get("name")
    )
    referenced = set(VARIABLE_RE.findall(raw_text))
    unknown = sorted(
        name for name in referenced if name not in defined and not name.startswith("__")
    )
    return [f"{path}: undefined dashboard variable ${{{name}}}" for name in unknown]


def _business_chart_scripts(panels: list[dict]) -> list[tuple[int, str]]:
    scripts: list[tuple[int, str]] = []
    for panel in panels:
        script = panel.get("options", {}).get("getOption")
        if isinstance(script, str) and script.strip():
            scripts.append((panel["id"], script))
    return scripts


def _validate_javascript(path: Path, panels: list[dict]) -> list[str]:
    node = shutil.which("node")
    scripts = _business_chart_scripts(panels)
    if not scripts or node is None:
        return []

    errors: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        for panel_id, script in scripts:
            script_path = Path(directory) / f"panel-{panel_id}.js"
            script_path.write_text(
                "function __validate_business_chart__() {\n" + script + "\n}\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [node, "--check", str(script_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode:
                detail = (result.stderr or result.stdout).strip()
                errors.append(f"{path}: panel {panel_id} JavaScript failed: {detail}")
    return errors


def main() -> None:
    paths = sorted(DASHBOARD_DIR.glob("*.json"))
    if not paths:
        raise SystemExit(f"no dashboard JSON files found under {DASHBOARD_DIR}")

    errors: list[str] = []
    for path in paths:
        raw_text = path.read_text(encoding="utf-8")
        dashboard = json.loads(raw_text)
        panels = _panels(dashboard)
        if not panels:
            errors.append(f"{path}: dashboard has no panels")
            continue
        errors.extend(_validate_layout(path, panels))
        errors.extend(_validate_variables(path, dashboard, raw_text))
        errors.extend(_validate_javascript(path, panels))
        print(f"OK: {path} ({len(panels)} panels)")

    if errors:
        raise SystemExit("Grafana validation failed:\n" + "\n".join(errors))


if __name__ == "__main__":
    main()
