# TypeScript SDK

Package: `@renzai/sdk` 0.1.0. Supported runtime: Node.js 20+ or a modern server runtime with
standards-based `fetch`. The package uses ESM, strict TypeScript, declaration output, and zero
production dependencies. It is a local workspace package and is not published to npm.

```ts
import { Renzai } from "@renzai/sdk";

const client = new Renzai({
  apiKey: process.env.RENZAI_API_KEY!,
  baseUrl: process.env.RENZAI_BASE_URL ?? "http://localhost:8000",
});
const analysis = await client.analyze({ content: "application-selected text", direction: "input" });
```

The caller may inject `fetch` and pass `AbortSignal` per request. The SDK owns no persistent
resource, so it exposes no artificial close method. `RenzaiSession` provides implemented Tier 2
session/CSRF operations. `iterIncidents` is an async generator bounded by `maxPages` and rejects a
repeated cursor.

This package is server-side. Never import an API-key-holding instance into a browser bundle. The
safe browser topology is browser → customer backend → Renzai.
