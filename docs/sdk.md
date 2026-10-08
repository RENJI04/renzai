# SDK usage

The typed SDKs mirror implemented API v1 and are installed from this repository. They are not
published packages yet.

## Python

```bash
python -m pip install -e ./packages/python-sdk
```

```python
import os
from renzai_sdk import Action, ChatMessage, Renzai, RenzaiError

try:
    with Renzai(
        api_key=os.environ["RENZAI_API_KEY"],
        base_url=os.environ.get("RENZAI_BASE_URL", "http://localhost:8080"),
    ) as client:
        result = client.analyze(content="Application-selected text", direction="input")
        if result.action in {Action.BLOCK, Action.REQUIRE_REVIEW}:
            print(f"withheld: {result.action}; request={result.request_id}")
        else:
            completion = client.gateway.create(
                model="configured-model",
                messages=[ChatMessage(role="user", content="Safe synthetic request")],
            )
            print(completion.content)
except RenzaiError as error:
    print(f"Renzai request failed safely: {error}")
```

`RenzaiSession` and `AsyncRenzaiSession` accept an existing opaque session token plus CSRF token for
incident, analytics, and advisory-AI operations. Do not put either credential in logs or a browser
bundle. See [Phase 12 examples](../examples/phase-12/README.md).

## TypeScript

Use the workspace package from a trusted Node.js/server runtime:

```bash
pnpm install --frozen-lockfile
```

```ts
import { Renzai, RenzaiError } from "@renzai/sdk";

const client = new Renzai({
  apiKey: process.env.RENZAI_API_KEY!,
  baseUrl: process.env.RENZAI_BASE_URL ?? "http://localhost:8080",
});

try {
  const result = await client.analyze({
    content: "Application-selected text",
    direction: "input",
  });
  console.log(result.action, result.requestId);
} catch (error) {
  if (error instanceof RenzaiError) console.error(error.code, error.requestId);
  else throw error;
}
```

Never instantiate an API-key client in public frontend code. Use browser → customer backend →
Renzai. Neither SDK recalculates risk/policy or converts AI advice into deterministic evidence.
