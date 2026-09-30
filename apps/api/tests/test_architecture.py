from __future__ import annotations

from pathlib import Path

EXPECTED_MODULES = {
    "auth",
    "users",
    "organizations",
    "memberships",
    "applications",
    "environments",
    "api_keys",
    "security",
    "detectors",
    "risk",
    "policies",
    "incidents",
    "logs",
    "providers",
    "gateway",
    "ai_intelligence",
    "audit",
    "notifications",
    "analytics",
}
FORBIDDEN_DOMAIN_IMPORTS = ("fastapi", "sqlalchemy", "redis", "celery", "httpx")


def test_phase_two_module_boundaries_are_present() -> None:
    modules_root = Path(__file__).parents[1] / "src" / "renzai" / "modules"
    assert {
        path.name
        for path in modules_root.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    } == EXPECTED_MODULES


def test_future_domain_code_cannot_depend_on_transport_or_infrastructure() -> None:
    modules_root = Path(__file__).parents[1] / "src" / "renzai" / "modules"
    violations: list[str] = []
    for domain_file in modules_root.glob("*/domain/**/*.py"):
        content = domain_file.read_text(encoding="utf-8")
        if any(
            f"import {dependency}" in content or f"from {dependency}" in content
            for dependency in FORBIDDEN_DOMAIN_IMPORTS
        ):
            violations.append(str(domain_file))
    assert violations == []
