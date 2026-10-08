from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_verifier() -> ModuleType:
    path = Path(__file__).parents[3] / "scripts/verify_phase16_assets.py"
    spec = importlib.util.spec_from_file_location("verify_phase16_assets", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase16_adoption_assets_are_complete_and_private() -> None:
    module = _load_verifier()
    assert module.verify() == []
