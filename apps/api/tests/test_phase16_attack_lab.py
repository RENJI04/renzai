from __future__ import annotations

import json
from pathlib import Path

from renzai.modules.security.domain.engine import SecurityEngine
from renzai.modules.security.domain.types import Category, Direction

ROOT = Path(__file__).parents[3]
SCENARIOS = ROOT / "examples" / "attack-lab" / "scenarios.json"


def test_attack_lab_covers_all_frozen_categories_and_controls() -> None:
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    categories = {item["category"] for item in scenarios}
    assert categories == {category.value for category in Category}
    for category in categories:
        matching = [item for item in scenarios if item["category"] == category]
        assert any(item["kind"] == "malicious" for item in matching)
        assert any(item["kind"] == "benign_control" for item in matching)
    encoded = {
        item["scenario_id"] for item in scenarios if item["category"] == "encoded_obfuscated"
    }
    assert {
        "obfuscation-base64",
        "obfuscation-percent",
        "obfuscation-html",
        "obfuscation-zero-width",
    }.issubset(encoded)


def test_attack_lab_curated_expectations_match_security_engine() -> None:
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    engine = SecurityEngine()
    for scenario in scenarios:
        result = engine.analyze(scenario["input"], Direction(scenario["direction"]))
        categories = {finding.category.value for finding in result.findings}
        expected = scenario["expected_category"]
        if expected is None:
            assert not categories, scenario["scenario_id"]
        else:
            assert expected in categories, scenario["scenario_id"]
