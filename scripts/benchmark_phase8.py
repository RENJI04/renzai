"""Local Phase 8 pure-path microbenchmark with a deterministic mock provider.

This intentionally excludes HTTP, authentication, and database persistence. It measures
the repeatable local message/analysis/normalization path and is not a production SLA.
"""

from __future__ import annotations

from statistics import median
from time import perf_counter_ns

from renzai.modules.gateway.domain import inspection_text
from renzai.modules.providers.domain import ChatMessage, ProviderChatRequest, ProviderCompletion
from renzai.modules.security.domain.engine import SecurityEngine
from renzai.modules.security.domain.types import Direction

REQUEST = ProviderChatRequest(
    model="benchmark-model",
    messages=(
        ChatMessage("system", "Answer accurately and concisely."),
        ChatMessage("user", "Summarize why deterministic security checks are useful."),
    ),
    temperature=0.2,
    max_tokens=128,
)


def mock_provider(_: ProviderChatRequest) -> ProviderCompletion:
    return ProviderCompletion(
        completion_id="chatcmpl-benchmark",
        created=1,
        model="benchmark-model",
        content="Deterministic checks are repeatable, inspectable, and provider-independent.",
        finish_reason="stop",
        usage={"prompt_tokens": 16, "completion_tokens": 9, "total_tokens": 25},
    )


def main(iterations: int = 2_000) -> None:
    engine = SecurityEngine()
    samples: dict[str, list[int]] = {
        "input_security": [],
        "provider": [],
        "output_security": [],
        "local_overhead_excluding_provider": [],
        "total": [],
    }
    for _ in range(iterations):
        started = perf_counter_ns()
        inspectable = inspection_text(REQUEST.messages)
        input_started = perf_counter_ns()
        engine.analyze(inspectable, Direction.INPUT)
        provider_started = perf_counter_ns()
        completion = mock_provider(REQUEST)
        output_started = perf_counter_ns()
        engine.analyze(completion.content, Direction.OUTPUT)
        response_started = perf_counter_ns()
        completion.response()
        finished = perf_counter_ns()

        input_ns = provider_started - input_started
        provider_ns = output_started - provider_started
        output_ns = response_started - output_started
        total_ns = finished - started
        samples["input_security"].append(input_ns)
        samples["provider"].append(provider_ns)
        samples["output_security"].append(output_ns)
        samples["local_overhead_excluding_provider"].append(total_ns - provider_ns)
        samples["total"].append(total_ns)

    print(f"iterations: {iterations}")
    print("scope: pure local path; excludes auth, persistence, Redis, and network I/O")
    for label, values in samples.items():
        print(f"{label}_median_ms: {median(values) / 1_000_000:.4f}")


if __name__ == "__main__":
    main()
