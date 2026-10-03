"""Adversarial local security-path benchmark; results are not a production SLA."""

from __future__ import annotations

import base64
from collections.abc import Callable
from statistics import median
from time import perf_counter

from renzai.modules.gateway.domain import inspection_text
from renzai.modules.providers.domain import ChatMessage
from renzai.modules.security.domain.engine import SecurityEngine
from renzai.modules.security.domain.types import Direction


def _measure(operation: Callable[[], object], iterations: int) -> float:
    samples: list[float] = []
    for _ in range(iterations):
        started = perf_counter()
        operation()
        samples.append((perf_counter() - started) * 1_000)
    return median(samples)


def _normalization_adversary() -> str:
    tokens = [
        base64.urlsafe_b64encode(bytes([65 + index]) * 1_536).decode("ascii") for index in range(8)
    ]
    prefix = " ".join(tokens)
    suffix = ("%41&amp;\\u0041 \t" * 2_000)[: 32_768 - len(prefix) - 1]
    return f"{prefix} {suffix}"


def main() -> None:
    engine = SecurityEngine()
    max_analyze = "A" * (32 * 1_024)
    adversarial = _normalization_adversary()
    messages = tuple(ChatMessage("user", f"message-{index}:" + "A" * 880) for index in range(32))
    gateway_text = inspection_text(messages)

    print("Phase 13 local adversarial benchmark (median milliseconds; not a production SLA)")
    print(f"max_analyze_bytes={len(max_analyze.encode('utf-8'))}")
    print(
        f"max_analyze_ms={_measure(lambda: engine.analyze(max_analyze, Direction.INPUT), 20):.4f}"
    )
    print(f"normalization_adversary_bytes={len(adversarial.encode('utf-8'))}")
    print(
        "normalization_adversary_ms="
        f"{_measure(lambda: engine.analyze(adversarial, Direction.INPUT), 20):.4f}"
    )
    print(f"gateway_messages={len(messages)} gateway_inspection_bytes={len(gateway_text.encode())}")
    print(
        "gateway_inspection_ms="
        f"{_measure(lambda: engine.analyze(gateway_text, Direction.INPUT), 20):.4f}"
    )


if __name__ == "__main__":
    main()
