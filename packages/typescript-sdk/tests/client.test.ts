import { describe, expect, it, vi } from "vitest";

import {
  AuthenticationError,
  AuthorizationError,
  ConfigurationError,
  ConflictError,
  InspectionError,
  NotFoundError,
  PolicyBlockError,
  ProviderError,
  RateLimitError,
  Renzai,
  RenzaiConnectionError,
  RenzaiProtocolError,
  RenzaiSession,
  RenzaiTimeoutError,
  ReviewRequiredError,
  ValidationError,
} from "../src/index.js";

function analyzePayload(): Record<string, unknown> {
  return {
    analysis_id: "01900000-0000-7000-8000-000000000001",
    event_id: "01900000-0000-7000-8000-000000000002",
    timestamp: "2026-10-03T00:00:00+00:00",
    direction: "input",
    source: "analyze",
    safe: false,
    no_detected_threat: false,
    action: "flag",
    risk_score: 43,
    severity: "medium",
    confidence: 90,
    risk_profile: { id: "profile", name: "renzai-v1", version: 1 },
    normalization_version: "1.0.0",
    detector_ruleset_version: "1.0.0",
    findings: [
      {
        finding_id: "01900000-0000-7000-8000-000000000003",
        detector_id: "prompt-injection",
        detector_version: "1.0.0",
        ruleset_version: "1.0.0",
        category: "prompt_injection",
        direction: "input",
        severity: "medium",
        confidence: 90,
        evidence: { kind: "pattern", label: "synthetic" },
        safe_explanation: "Synthetic prompt-injection indicator.",
        metadata: {},
      },
    ],
    risk_contributions: [],
    risk_explanation: { base_score: 43 },
    policy_decision: {
      policy_decision_id: "01900000-0000-7000-8000-000000000004",
      policy_match: null,
      evaluated_policy_versions: [],
      scope_winners: [],
      rationale_code: "no_policy_matched",
      redaction_targets: [],
    },
    timing: { total_ms: 2 },
    correlation_id: "corr-safe",
    future_additive_field: true,
  };
}

function incidentPayload(identifier = "incident-1"): Record<string, unknown> {
  return {
    incident_id: identifier,
    organization_id: "org-1",
    application_id: null,
    environment_id: null,
    status: "open",
    severity: "high",
    source: "manual",
    title: "Synthetic incident",
    safe_summary: "Safe synthetic summary.",
    version: 1,
    created_at: "2026-10-03T00:00:00+00:00",
    updated_at: "2026-10-03T00:00:00+00:00",
    assignee_user_id: null,
    action: null,
    risk_score: null,
    category: null,
    resolved_at: null,
  };
}

function aiPayload(): Record<string, unknown> {
  return {
    request_id: "ai-request-1",
    incident_id: "incident-1",
    task_type: "incident_summary",
    status: "pending",
    ai_generated: true,
    context_mode: "redacted",
    incident_version: 1,
    provider_id: "provider-1",
    provider_name: "Synthetic provider",
    model: "synthetic-model",
    prompt_template_version: null,
    input_context_version: "1.0.0",
    output_schema_version: "1.0.0",
    content: null,
    usage: null,
    error_code: null,
    created_at: "2026-10-03T00:00:00+00:00",
    completed_at: null,
  };
}

function jsonResponse(payload: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  return new Response(JSON.stringify(payload), {
    status: init.status ?? 200,
    headers,
  });
}

describe("Renzai application-key client", () => {
  it("rejects base URLs that embed credentials", () => {
    expect(
      () =>
        new Renzai({
          apiKey: "rz_dev_example_not_real",
          baseUrl: "https://username:password@renzai.example",
        }),
    ).toThrow("absolute HTTP");
  });

  it("serializes Analyze, authenticates, exposes request IDs, and hides the key", async () => {
    const secret = "rz_dev_example_not_real";
    const fetch = vi.fn<typeof globalThis.fetch>(async (_input, init) => {
      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe(`Bearer ${secret}`);
      expect(headers.get("User-Agent")).toBe("Renzai-TypeScript/0.1.0");
      expect(JSON.parse(init?.body as string)).toEqual({
        content: "safe synthetic text",
        direction: "input",
        correlation_id: "corr-safe",
        metadata: { feature: "test" },
      });
      return jsonResponse(analyzePayload(), {
        headers: { "X-Request-ID": "req-1" },
      });
    });
    const client = new Renzai({
      apiKey: secret,
      baseUrl: "https://renzai.example",
      fetch,
    });

    const result = await client.analyze({
      content: "safe synthetic text",
      direction: "input",
      correlationId: "corr-safe",
      metadata: { feature: "test" },
    });

    expect(result.action).toBe("flag");
    expect(result.requestId).toBe("req-1");
    expect(fetch).toHaveBeenCalledWith(
      "https://renzai.example/api/v1/analyze",
      expect.anything(),
    );
    expect(client.toString()).not.toContain(secret);
  });

  it("keeps the Gateway text-only and non-streaming", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(async (_input, init) => {
      expect(JSON.parse(init?.body as string)).toEqual({
        model: "safe-model",
        messages: [{ role: "user", content: "Synthetic prompt" }],
        stream: false,
        temperature: 0.2,
        max_tokens: 20,
      });
      return jsonResponse(
        {
          id: "chatcmpl-1",
          created: 1,
          model: "safe-model",
          choices: [
            {
              index: 0,
              message: { role: "assistant", content: "Safe answer." },
              finish_reason: "stop",
            },
          ],
          usage: { prompt_tokens: 2, completion_tokens: 2, total_tokens: 4 },
        },
        {
          headers: {
            "X-Renzai-Request-ID": "gateway-1",
            "X-Renzai-Input-Action": "allow",
            "X-Renzai-Output-Action": "redact",
          },
        },
      );
    });
    const client = new Renzai({
      apiKey: "rz_dev_example_not_real",
      baseUrl: "https://renzai.example",
      fetch,
    });

    const result = await client.gateway.create({
      model: "safe-model",
      messages: [{ role: "user", content: "Synthetic prompt" }],
      temperature: 0.2,
      maxTokens: 20,
    });

    expect(result.content).toBe("Safe answer.");
    expect(result.outputAction).toBe("redact");
    await expect(
      client.gateway.create({
        model: "safe-model",
        messages: [{ role: "user", content: "Synthetic prompt" }],
        stream: true,
      } as never),
    ).rejects.toThrow("Unsupported request field: stream");
    await expect(
      client.gateway.create({
        model: "safe-model",
        messages: [{ role: "user", content: "Synthetic prompt" }],
        tools: [],
      } as never),
    ).rejects.toThrow("Unsupported request field: tools");
  });
});

describe("error handling and transport safety", () => {
  const matrix = [
    ["validation", 422, ValidationError],
    ["authentication", 401, AuthenticationError],
    ["authorization", 403, AuthorizationError],
    ["policy_block", 403, PolicyBlockError],
    ["not_found_or_hidden", 404, NotFoundError],
    ["conflict", 409, ConflictError],
    ["review_required", 409, ReviewRequiredError],
    ["rate_limit", 429, RateLimitError],
    ["provider_error", 502, ProviderError],
    ["inspection_failure", 503, InspectionError],
    ["configuration_error", 503, ConfigurationError],
    ["provider_timeout", 504, RenzaiTimeoutError],
  ] as const;

  it.each(matrix)("maps %s errors", async (code, status, ErrorType) => {
    const client = new Renzai({
      apiKey: "rz_dev_example_not_real",
      baseUrl: "https://renzai.example",
      fetch: async () =>
        jsonResponse(
          {
            error: {
              code,
              message: "Safe message.",
              request_id: "request-error",
              details: { phase: "input" },
            },
          },
          { status },
        ),
    });
    const caught = await client
      .analyze({ content: "synthetic", direction: "input" })
      .catch((error: unknown) => error);
    expect(caught).toBeInstanceOf(ErrorType);
    expect(caught).toMatchObject({
      code,
      requestId: "request-error",
      statusCode: status,
      details: { phase: "input" },
    });
  });

  it("does not retry POST but safely retries a GET connection failure", async () => {
    let postCalls = 0;
    const postClient = new Renzai({
      apiKey: "rz_dev_example_not_real",
      baseUrl: "https://renzai.example",
      retry: { maxAttempts: 3, initialBackoffMs: 0 },
      fetch: async () => {
        postCalls += 1;
        throw new TypeError("connection failed");
      },
    });
    await expect(
      postClient.analyze({ content: "synthetic", direction: "input" }),
    ).rejects.toBeInstanceOf(RenzaiConnectionError);
    expect(postCalls).toBe(1);

    let getCalls = 0;
    const session = new RenzaiSession({
      sessionToken: "opaque-session",
      csrfToken: "csrf-safe",
      cookieName: "renzai_session",
      baseUrl: "https://renzai.example",
      retry: { maxAttempts: 2, initialBackoffMs: 0 },
      fetch: async () => {
        getCalls += 1;
        if (getCalls === 1) throw new TypeError("connection failed");
        return jsonResponse({
          items: [incidentPayload()],
          next_cursor: null,
          limit: 50,
        });
      },
    });
    expect((await session.listIncidents("org-1")).items).toHaveLength(1);
    expect(getCalls).toBe(2);
  });

  it("preserves AbortSignal cancellation and rejects malformed/oversized responses", async () => {
    const controller = new AbortController();
    const abortError = new DOMException("cancelled", "AbortError");
    const abortingClient = new Renzai({
      apiKey: "rz_dev_example_not_real",
      baseUrl: "https://renzai.example",
      fetch: async (_input, init) => {
        controller.abort(abortError);
        throw init?.signal?.reason;
      },
    });
    await expect(
      abortingClient.analyze(
        { content: "synthetic", direction: "input" },
        { signal: controller.signal },
      ),
    ).rejects.toBe(abortError);

    const malformedClient = new Renzai({
      apiKey: "rz_dev_example_not_real",
      baseUrl: "https://renzai.example",
      fetch: async () => jsonResponse({ analysis_id: "partial" }),
    });
    await expect(
      malformedClient.analyze({ content: "synthetic", direction: "input" }),
    ).rejects.toBeInstanceOf(RenzaiProtocolError);

    const boundedClient = new Renzai({
      apiKey: "rz_dev_example_not_real",
      baseUrl: "https://renzai.example",
      maxResponseBytes: 4,
      fetch: async () => jsonResponse({ too_large: true }),
    });
    await expect(
      boundedClient.analyze({ content: "synthetic", direction: "input" }),
    ).rejects.toThrow("size limit");
  });

  it("normalizes the SDK network timeout without retrying Analyze", async () => {
    let calls = 0;
    const client = new Renzai({
      apiKey: "rz_dev_example_not_real",
      baseUrl: "https://renzai.example",
      timeoutMs: 1,
      retry: { maxAttempts: 3 },
      fetch: async (_input, init) => {
        calls += 1;
        await new Promise<never>((_resolve, reject) => {
          init?.signal?.addEventListener(
            "abort",
            () => {
              const reason: unknown = init.signal?.reason;
              reject(
                reason instanceof Error
                  ? reason
                  : new DOMException(
                      "The operation was aborted.",
                      "AbortError",
                    ),
              );
            },
            { once: true },
          );
        });
        throw new Error("unreachable");
      },
    });

    await expect(
      client.analyze({ content: "synthetic", direction: "input" }),
    ).rejects.toBeInstanceOf(RenzaiTimeoutError);
    expect(calls).toBe(1);
  });
});

describe("session client", () => {
  it("sends CSRF and caller idempotency headers and parses AI results", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(async (_input, init) => {
      const headers = new Headers(init?.headers);
      expect(headers.get("Cookie")).toBe("renzai_session=opaque-session");
      expect(headers.get("X-Renzai-CSRF")).toBe("csrf-safe");
      expect(headers.get("Idempotency-Key")).toBe("caller-key");
      return jsonResponse(aiPayload(), {
        status: 202,
        headers: { "X-Request-ID": "req-ai" },
      });
    });
    const client = new RenzaiSession({
      sessionToken: "opaque-session",
      csrfToken: "csrf-safe",
      cookieName: "renzai_session",
      baseUrl: "https://renzai.example",
      fetch,
    });

    const result = await client.requestAI("org-1", "incident-1", {
      taskType: "incident_summary",
      idempotencyKey: "caller-key",
    });

    expect(result.aiGenerated).toBe(true);
    expect(result.responseRequestId).toBe("req-ai");
    expect(client.toString()).not.toContain("opaque-session");
  });

  it.each([
    ["session token", { sessionToken: "session\u0000value" }],
    ["CSRF token", { csrfToken: "csrf value" }],
    ["base URL", { baseUrl: "https://renzai.example\n.attacker.example" }],
  ])("rejects an unsafe %s without echoing it", (_label, override) => {
    const options = {
      sessionToken: "opaque-session",
      csrfToken: "csrf-safe",
      baseUrl: "https://renzai.example",
      ...override,
    };
    const unsafeValue = Object.values(override)[0];
    try {
      new RenzaiSession(options);
      throw new Error("constructor unexpectedly succeeded");
    } catch (error: unknown) {
      expect(error).toBeInstanceOf(TypeError);
      expect(String(error)).not.toContain(unsafeValue);
    }
  });

  it("rejects unsafe caller idempotency before the network", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>();
    const client = new RenzaiSession({
      sessionToken: "opaque-session",
      csrfToken: "csrf-safe",
      baseUrl: "https://renzai.example",
      fetch,
    });
    await expect(
      client.requestAI("org-1", "incident-1", {
        taskType: "incident_summary",
        idempotencyKey: "unsafe\tkey",
      }),
    ).rejects.toThrow("idempotencyKey");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("parses analytics and guards against repeated cursors", async () => {
    let calls = 0;
    const client = new RenzaiSession({
      sessionToken: "opaque-session",
      csrfToken: "csrf-safe",
      cookieName: "renzai_session",
      baseUrl: "https://renzai.example",
      fetch: async (input) => {
        const url = input instanceof Request ? input.url : input.toString();
        if (url.includes("/analytics/dashboard")) {
          return jsonResponse({
            filters: { window: "24h" },
            summary: {},
            activity: [],
            risk_distribution: [],
            threat_categories: [],
            top_detectors: [],
            policy_actions: [],
            applications: [],
            environments: [],
            providers: [],
            incidents: {},
            recent_incidents: [],
            query_duration_ms: 3,
          });
        }
        calls += 1;
        return jsonResponse({
          items: [incidentPayload(`incident-${String(calls)}`)],
          next_cursor: "repeat",
          limit: 1,
        });
      },
    });

    expect((await client.analytics("org-1")).queryDurationMs).toBe(3);
    const consume = async (): Promise<void> => {
      for await (const incident of client.iterIncidents("org-1", {
        pageSize: 1,
      })) {
        expect(incident.incidentId).toContain("incident-");
      }
    };
    await expect(consume()).rejects.toThrow("repeated");
    expect(calls).toBe(2);
  });
});
