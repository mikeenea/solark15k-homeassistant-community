"""Load dependency-free integration modules without importing Home Assistant."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_integration_module(name: str) -> ModuleType:
    """Load one module directly from custom_components/solark15k."""
    path = ROOT / "custom_components" / "solark15k" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"solark15k_test_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
