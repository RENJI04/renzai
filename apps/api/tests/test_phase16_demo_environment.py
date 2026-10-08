from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[3]


def _module() -> ModuleType:
    path = ROOT / "scripts" / "prepare_demo_env.py"
    spec = importlib.util.spec_from_file_location("prepare_demo_env", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_demo_environment_is_random_local_and_not_production(tmp_path: Path) -> None:
    module = _module()
    first = module.render_demo_environment()
    second = module.render_demo_environment()
    assert first != second
    assert "RENZAI_APP_ENVIRONMENT=development" in first
    assert "RENZAI_APP_PUBLIC_BASE_URL=http://localhost:8080" in first
    assert "RENZAI_SESSION_SECURE_COOKIE=false" in first
    assert "replace-" not in first

    target = tmp_path / ".env.demo"
    module.create_demo_environment(target)
    assert target.read_text(encoding="utf-8").startswith("COMPOSE_PROJECT_NAME=renzai-demo")
    with pytest.raises(FileExistsError):
        module.create_demo_environment(target)
