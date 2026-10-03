# Python SDK

Package: `renzai-sdk` 0.1.0. Import: `renzai_sdk`. The distinct import avoids ambiguity with the
backend's `renzai` package. Supported Python: 3.11 and newer. The package is typed and includes
`py.typed`.

Install locally from the repository; it is not published to PyPI:

```bash
python -m pip install -e ./packages/python-sdk
```

```python
import os
from renzai_sdk import ChatMessage, Renzai

with Renzai(api_key=os.environ["RENZAI_API_KEY"], base_url="http://localhost:8000") as client:
    analysis = client.analyze(content="application-selected text", direction="input")
    completion = client.gateway.create(
        model="configured-model",
        messages=[ChatMessage(role="user", content="application-selected text")],
    )
```

`AsyncRenzai` mirrors these methods and supports `async with`. Cancellation is not caught or
converted. Session clients expose `list_incidents`, bounded `iter_incidents`, `get_incident`,
status/assignment/comment operations with visible optimistic `version`, dashboard analytics, and
request/list/get AI intelligence. `request_ai` accepts a caller-controlled `idempotency_key`.

Application-key credentials never appear in `repr`. Context managers close owned `httpx` clients.
An injected transport is owned and closed through `httpx` client semantics.
