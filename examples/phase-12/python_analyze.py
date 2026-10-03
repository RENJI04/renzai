"""Analyze only the application-selected text before an LLM call."""

import os

from renzai_sdk import Action, Renzai

with Renzai(
    api_key=os.environ["RENZAI_API_KEY"],
    base_url=os.environ.get("RENZAI_BASE_URL", "http://localhost:8000"),
) as client:
    result = client.analyze(content="Safe synthetic example", direction="input")

if result.action in {Action.BLOCK, Action.REQUIRE_REVIEW}:
    print(f"Model call withheld: {result.action}; request_id={result.request_id}")
elif result.action is Action.REDACT:
    print("Use result.redacted_content if present; do not redact independently.")
else:
    print(f"Server action: {result.action}; request_id={result.request_id}")
