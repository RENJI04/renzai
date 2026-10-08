"""Run the safe Attack Lab corpus through the local Python SDK."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parents[2]
SDK_SOURCE = ROOT / "packages" / "python-sdk" / "src"
sys.path.insert(0, str(SDK_SOURCE))

from renzai_sdk import Direction, Renzai  # noqa: E402

SCENARIOS = Path(__file__).with_name("scenarios.json")


def load_scenarios() -> list[dict[str, Any]]:
    value = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("Attack Lab corpus must be a JSON list")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    parser.add_argument("--kind", choices=("malicious", "benign_control", "boundary"))
    arguments = parser.parse_args()
    api_key = os.environ.get("RENZAI_API_KEY")
    if not api_key:
        print("RENZAI_API_KEY is required; keep it in the trusted server shell.", file=sys.stderr)
        return 2

    scenarios = [
        item
        for item in load_scenarios()
        if arguments.kind is None or item["kind"] == arguments.kind
    ]
    results: list[dict[str, object]] = []
    with Renzai(
        api_key=api_key,
        base_url=os.environ.get("RENZAI_BASE_URL", "http://localhost:8080"),
    ) as client:
        for scenario in scenarios:
            analysis = client.analyze(
                content=str(scenario["input"]), direction=Direction(str(scenario["direction"]))
            )
            category_names = sorted({finding.category.value for finding in analysis.findings})
            expected = scenario["expected_category"]
            passed = expected in category_names if expected else not category_names
            results.append(
                {
                    "scenario_id": scenario["scenario_id"],
                    "kind": scenario["kind"],
                    "action": analysis.action.value,
                    "categories": category_names,
                    "passed": passed,
                    "request_id": analysis.request_id,
                }
            )

    if arguments.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            mark = "PASS" if result["passed"] else "FAIL"
            rendered_categories = ", ".join(cast(list[str], result["categories"])) or "none"
            print(
                f"{mark:4} {result['scenario_id']:<38} "
                f"action={result['action']:<14} categories={rendered_categories}"
            )
        passed_count = sum(bool(item["passed"]) for item in results)
        print(f"\n{passed_count}/{len(results)} curated cases passed")
    return 0 if all(item["passed"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
