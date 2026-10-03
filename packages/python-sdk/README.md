# Renzai Python SDK

Typed synchronous and asynchronous clients for Renzai API v1. The distribution is named
`renzai-sdk` and the import is `renzai_sdk` to avoid colliding with the server's `renzai`
package. Version: `0.1.0`.

This package is built locally and is not published to PyPI. From the repository root:

```bash
python -m pip install -e ./packages/python-sdk
```

## Analyze and Gateway

```python
import os
from renzai_sdk import Action, ChatMessage, Renzai

with Renzai(
    api_key=os.environ["RENZAI_API_KEY"],
    base_url=os.environ.get("RENZAI_BASE_URL", "http://localhost:8000"),
) as client:
    analysis = client.analyze(content="Text selected by the application", direction="input")
    if analysis.action in {Action.BLOCK, Action.REQUIRE_REVIEW}:
        raise RuntimeError(f"Renzai action: {analysis.action}")

    completion = client.gateway.create(
        model="configured-model",
        messages=[ChatMessage(role="user", content="Text selected by the application")],
    )
    print(completion.content)
```

The Gateway is Renzai's limited, non-streaming, text-only `/v1/chat/completions` endpoint. It
does not expose tools, functions, multimodal content, streaming, or arbitrary passthrough fields,
and it is not an OpenAI SDK drop-in replacement.

`AsyncRenzai` provides the same application-key methods with `async with`. The separate
`RenzaiSession` and `AsyncRenzaiSession` clients support implemented incidents, analytics, and AI
intelligence operations using an existing server-side user session plus CSRF token. Application
keys do not authorize those control-plane routes.

## Errors, timeouts, and retries

```python
from renzai_sdk import RateLimitError, RenzaiError

try:
    result = client.analyze(content="selected text", direction="input")
except RateLimitError as error:
    print(error.code, error.request_id, error.status_code)
except RenzaiError as error:
    print(error.code, error.request_id)
```

Errors preserve only the server's safe message, code, safe details, request ID, and status. The
default transport timeout is 30 seconds. Automatic retries are limited to safe GET connection
failures and safe GET `429` responses with numeric `Retry-After`; POST/PATCH, Gateway, Analyze,
and AI generation requests are not retried. `RetryPolicy` bounds attempts and backoff. Responses
are streamed into a bounded buffer (2 MiB by default).

## Security and compatibility

- Python 3.11+; Renzai API v1; production dependency: `httpx`.
- Keep `RENZAI_API_KEY` in server-side environment configuration. Never place it in browser code.
- Logging is off by default. An optional logger receives method, route template, status, request
  ID, and duration only—not credentials or content.
- TLS verification and normal `httpx` proxy/environment behavior remain enabled by default.
- The SDK contacts only the configured Renzai base URL and has no telemetry.
- The repository currently contains no project license file, so this local package deliberately
  declares no separate SDK license and must not be published until project licensing is resolved.

See `docs/phase-12/` for complete integration and security guidance.
