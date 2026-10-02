"""Local Phase 11 overhead microbenchmark; excludes model/network latency."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from statistics import median
from time import perf_counter

from renzai.modules.ai_intelligence.application import scrub_text
from renzai.modules.ai_intelligence.domain import AITaskType, parse_task_output


def measure(operation: Callable[[], object], iterations: int = 1000) -> float:
    samples: list[float] = []
    for _ in range(iterations):
        started = perf_counter()
        operation()
        samples.append((perf_counter() - started) * 1000)
    return median(samples)


def main() -> None:
    sensitive = "attacker@example.com called +1 415 555 1212 token=synthetic-secret-value"
    output = json.dumps({"summary": "Advisory summary", "key_points": ["Blocked input"]})
    context_source = {
        "incident": {"status": "open", "severity": "high", "risk_score": 84},
        "deterministic_findings": [
            {"detector_id": "prompt-injection-v1", "category": "prompt_injection"}
        ],
    }
    database = sqlite3.connect(":memory:")
    database.execute("CREATE TABLE results (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")

    def context_build() -> None:
        json.dumps(
            {"context_version": "1.0.0", "untrusted_incident_data": context_source},
            separators=(",", ":"),
            sort_keys=True,
        )

    def persist() -> None:
        database.execute("INSERT INTO results(payload) VALUES (?)", (output,))
        database.rollback()

    print("Phase 11 local overhead (median milliseconds; provider latency excluded)")
    print(f"context_build_ms={measure(context_build):.4f}")
    print(f"redaction_ms={measure(lambda: scrub_text(sensitive)):.4f}")
    print(
        "schema_validation_ms="
        f"{measure(lambda: parse_task_output(AITaskType.INCIDENT_SUMMARY, output)):.4f}"
    )
    print(f"persistence_ms={measure(persist):.4f}")


if __name__ == "__main__":
    main()
