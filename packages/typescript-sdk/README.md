# @renzai/sdk

Strict TypeScript clients for Renzai API v1. Version: `0.1.0`.

This workspace package is built locally and is not published to npm. From the repository root:

```bash
pnpm --dir packages/typescript-sdk build
```

An internal workspace consumer may depend on `@renzai/sdk` with `workspace:*`.

## Analyze and Gateway

```ts
import { Renzai } from "@renzai/sdk";

const client = new Renzai({
  apiKey: process.env.RENZAI_API_KEY!,
  baseUrl: process.env.RENZAI_BASE_URL ?? "http://localhost:8000",
});

const analysis = await client.analyze({
  content: "Text selected by the application",
  direction: "input",
});

const completion = await client.gateway.create({
  model: "configured-model",
  messages: [{ role: "user", content: "Text selected by the application" }],
});
```

The Gateway client is deliberately limited to Renzai's non-streaming, text-only
`/v1/chat/completions` contract. It rejects unknown request fields at runtime and does not expose
streaming, tools, functions, or multimodal input. It is not an OpenAI SDK drop-in replacement.

`RenzaiSession` explicitly supports implemented incident, analytics, and AI intelligence routes
using an existing user session and CSRF token. These are not application-key routes.

## Errors, cancellation, and retries

```ts
import { RateLimitError, RenzaiError } from "@renzai/sdk";

try {
  await client.analyze({ content: "selected text", direction: "input" });
} catch (error) {
  if (error instanceof RateLimitError) console.error(error.requestId);
  else if (error instanceof RenzaiError)
    console.error(error.code, error.requestId);
}
```

Pass `{ signal }` as the second method argument for caller cancellation. The default timeout is
30 seconds. Retries are bounded and limited to safe GET connection failures and safe GET `429`
responses with numeric `Retry-After`; POST/PATCH, Analyze, Gateway, and AI generation calls are
not retried. Responses are streamed into a bounded 2 MiB buffer by default.

## Security and compatibility

- Node.js 20+ or a modern server runtime with standards-based `fetch`; Renzai API v1.
- **Never embed an application API key in a public browser/frontend bundle.** Route browser
  requests through your backend: browser → customer backend → Renzai.
- The core package has zero production dependencies and accepts custom `fetch` for tests/runtimes.
- Logging is off by default and, when enabled, receives only method, safe route template, status,
  request ID, and duration—not credentials or request/response content.
- TLS verification and runtime-standard proxy behavior remain enabled. There is no telemetry.
- The repository currently contains no project license file, so this local package deliberately
  declares no separate SDK license and must not be published until project licensing is resolved.

See `docs/phase-12/` for complete integration and security guidance.
