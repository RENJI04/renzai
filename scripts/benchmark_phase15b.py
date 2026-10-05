"""Measure local HTTP and deterministic Analyze/Gateway metric overhead."""

from __future__ import annotations

import json
import statistics
from collections.abc import Callable
from time import perf_counter

from fastapi.testclient import TestClient

from renzai.app import create_app
from renzai.core.config import Settings
from renzai.infrastructure.observability.metrics import record_security_operation
from renzai.modules.gateway.domain import inspection_text
from renzai.modules.providers.domain import ChatMessage
from renzai.modules.security.domain.engine import SecurityEngine
from renzai.modules.security.domain.types import Direction

ITERATIONS = 500
SECURITY_ITERATIONS = 1_000


def _measure(*, metrics_enabled: bool) -> list[float]:
    settings = Settings(
        app_environment="test",
        logging_level="CRITICAL",
        logging_json=False,
        observability_metrics_enabled=metrics_enabled,
    )
    samples: list[float] = []
    with TestClient(create_app(settings)) as client:
        for _ in range(20):
            assert client.get("/health").status_code == 200
        for _ in range(ITERATIONS):
            started = perf_counter()
            response = client.get("/health")
            samples.append((perf_counter() - started) * 1000)
            assert response.status_code == 200
    return samples


def _summary(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    return {
        "mean_ms": round(statistics.mean(samples), 4),
        "median_ms": round(statistics.median(samples), 4),
        "p95_ms": round(ordered[int(len(ordered) * 0.95) - 1], 4),
    }


def _compare_security_operation(
    operation: Callable[[], None], metric_name: str, metric_outcome: str
) -> dict[str, object]:
    def measure(record_metric: bool) -> list[float]:
        samples: list[float] = []
        for _ in range(SECURITY_ITERATIONS):
            started = perf_counter()
            operation()
            if record_metric:
                record_security_operation(metric_name, metric_outcome)
            samples.append((perf_counter() - started) * 1000)
        return samples

    baseline = measure(False)
    observed = measure(True)
    return {
        "iterations_per_mode": SECURITY_ITERATIONS,
        "without_metric": _summary(baseline),
        "with_metric": _summary(observed),
        "median_delta_ms": round(statistics.median(observed) - statistics.median(baseline), 4),
        "scope": "pure deterministic operation; excludes auth, persistence, Redis, and network I/O",
    }


def main() -> None:
    disabled = _measure(metrics_enabled=False)
    enabled = _measure(metrics_enabled=True)
    disabled_mean = statistics.mean(disabled)
    enabled_mean = statistics.mean(enabled)
    engine = SecurityEngine()
    analyze_text = "Summarize why deterministic security checks are useful."
    gateway_input = inspection_text(
        (
            ChatMessage("system", "Answer accurately and concisely."),
            ChatMessage("user", analyze_text),
        )
    )
    gateway_output = "Deterministic checks are repeatable and inspectable."

    def analyze_operation() -> None:
        engine.analyze(analyze_text, Direction.INPUT)

    def gateway_operation() -> None:
        engine.analyze(gateway_input, Direction.INPUT)
        engine.analyze(gateway_output, Direction.OUTPUT)

    print(
        json.dumps(
            {
                "http_health": {
                    "iterations_per_mode": ITERATIONS,
                    "metrics_disabled": _summary(disabled),
                    "metrics_enabled": _summary(enabled),
                    "mean_delta_ms": round(enabled_mean - disabled_mean, 4),
                    "mean_delta_percent": round(
                        ((enabled_mean / disabled_mean) - 1) * 100 if disabled_mean else 0.0,
                        2,
                    ),
                    "scope": "local TestClient /health; excludes network and exporter latency",
                },
                "analyze": _compare_security_operation(analyze_operation, "analysis", "allow"),
                "gateway_inspection": _compare_security_operation(
                    gateway_operation, "gateway", "completed"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
