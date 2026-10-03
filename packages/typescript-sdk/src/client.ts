import { RenzaiProtocolError } from "./errors.js";
import {
  asObject,
  parseAI,
  parseAnalytics,
  parseAnalyze,
  parseChat,
  parseIncident,
  parseIncidentPage,
  requestId,
} from "./protocol.js";
import { Transport } from "./transport.js";
import type { SafeLogEvent } from "./transport.js";
import type {
  AIIntelligenceResult,
  AITaskType,
  AnalyzeInput,
  AnalyzeResult,
  AnalyticsDashboard,
  ChatCompletion,
  ChatCompletionInput,
  DisclosureMode,
  Incident,
  IncidentFilters,
  IncidentPage,
  IncidentStatus,
  JsonObject,
  RequestOptions,
  RetryPolicy,
} from "./types.js";

export type RenzaiOptions = {
  apiKey: string;
  baseUrl: string;
  timeoutMs?: number;
  retry?: RetryPolicy;
  fetch?: typeof globalThis.fetch;
  logger?: (event: SafeLogEvent) => void;
  maxResponseBytes?: number;
};

export type RenzaiSessionOptions = {
  sessionToken: string;
  csrfToken: string;
  baseUrl: string;
  cookieName?: "__Host-renzai_session" | "renzai_session";
  timeoutMs?: number;
  retry?: RetryPolicy;
  fetch?: typeof globalThis.fetch;
  logger?: (event: SafeLogEvent) => void;
};

function headerSafe(value: string, label: string): string {
  if (!value || /[\r\n]/u.test(value))
    throw new TypeError(`${label} must be a non-empty header-safe value`);
  return value;
}

function assertAllowedKeys(value: object, allowed: readonly string[]): void {
  const unexpected = Object.keys(value).filter((key) => !allowed.includes(key));
  if (unexpected.length > 0)
    throw new TypeError(
      `Unsupported request field: ${unexpected.at(0) ?? "unknown"}`,
    );
}

function chatBody(input: ChatCompletionInput): JsonObject {
  assertAllowedKeys(input, [
    "model",
    "messages",
    "temperature",
    "topP",
    "maxTokens",
    "stop",
    "presencePenalty",
    "frequencyPenalty",
    "seed",
  ]);
  if (!input.model.trim()) throw new TypeError("model cannot be blank");
  if (input.messages.length < 1 || input.messages.length > 32) {
    throw new RangeError("messages must contain between 1 and 32 items");
  }
  for (const message of input.messages) {
    assertAllowedKeys(message, ["role", "content"]);
    if (
      !["system", "user", "assistant"].includes(message.role) ||
      !message.content.trim()
    ) {
      throw new TypeError(
        "message role and content must match the text-only Gateway contract",
      );
    }
  }
  if (
    input.temperature !== undefined &&
    (input.temperature < 0 || input.temperature > 2)
  ) {
    throw new RangeError("temperature must be between 0 and 2");
  }
  if (input.topP !== undefined && (input.topP <= 0 || input.topP > 1)) {
    throw new RangeError("topP must be greater than 0 and at most 1");
  }
  if (
    input.maxTokens !== undefined &&
    (input.maxTokens < 1 || input.maxTokens > 4096)
  ) {
    throw new RangeError("maxTokens must be between 1 and 4096");
  }
  for (const [label, value] of [
    ["presencePenalty", input.presencePenalty],
    ["frequencyPenalty", input.frequencyPenalty],
  ] as const) {
    if (value !== undefined && (value < -2 || value > 2)) {
      throw new RangeError(`${label} must be between -2 and 2`);
    }
  }
  if (
    input.seed !== undefined &&
    (!Number.isInteger(input.seed) ||
      input.seed < -(2 ** 31) ||
      input.seed > 2 ** 31 - 1)
  ) {
    throw new RangeError("seed must be a signed 32-bit integer");
  }
  if (input.stop !== undefined) {
    const stops = typeof input.stop === "string" ? [input.stop] : input.stop;
    if (
      stops.length < 1 ||
      stops.length > 4 ||
      stops.some((item) => !item || item.length > 1024)
    ) {
      throw new RangeError("stop must contain one to four bounded strings");
    }
  }
  return {
    model: input.model,
    messages: input.messages.map((message) => ({
      role: message.role,
      content: message.content,
    })),
    stream: false,
    ...(input.temperature === undefined
      ? {}
      : { temperature: input.temperature }),
    ...(input.topP === undefined ? {} : { top_p: input.topP }),
    ...(input.maxTokens === undefined ? {} : { max_tokens: input.maxTokens }),
    ...(input.stop === undefined ? {} : { stop: input.stop }),
    ...(input.presencePenalty === undefined
      ? {}
      : { presence_penalty: input.presencePenalty }),
    ...(input.frequencyPenalty === undefined
      ? {}
      : { frequency_penalty: input.frequencyPenalty }),
    ...(input.seed === undefined ? {} : { seed: input.seed }),
  };
}

class GatewayResource {
  readonly #transport: Transport;

  constructor(transport: Transport) {
    this.#transport = transport;
  }

  async create(
    input: ChatCompletionInput,
    options: RequestOptions = {},
  ): Promise<ChatCompletion> {
    const result = await this.#transport.request(
      "POST",
      "/v1/chat/completions",
      {
        body: chatBody(input),
        route: "/v1/chat/completions",
        ...options,
      },
    );
    return parseChat(result.data, result.response.headers);
  }
}

export class Renzai {
  readonly #transport: Transport;
  readonly gateway: GatewayResource;

  constructor(options: RenzaiOptions) {
    assertAllowedKeys(options, [
      "apiKey",
      "baseUrl",
      "timeoutMs",
      "retry",
      "fetch",
      "logger",
      "maxResponseBytes",
    ]);
    this.#transport = new Transport({
      baseUrl: options.baseUrl,
      headers: {
        Authorization: `Bearer ${headerSafe(options.apiKey, "apiKey")}`,
      },
      ...(options.timeoutMs === undefined
        ? {}
        : { timeoutMs: options.timeoutMs }),
      ...(options.retry === undefined ? {} : { retry: options.retry }),
      ...(options.fetch === undefined ? {} : { fetch: options.fetch }),
      ...(options.logger === undefined ? {} : { logger: options.logger }),
      ...(options.maxResponseBytes === undefined
        ? {}
        : { maxResponseBytes: options.maxResponseBytes }),
    });
    this.gateway = new GatewayResource(this.#transport);
  }

  toString(): string {
    return `Renzai(baseUrl=${JSON.stringify(this.#transport.baseUrl)})`;
  }

  async analyze(
    input: AnalyzeInput,
    options: RequestOptions = {},
  ): Promise<AnalyzeResult> {
    assertAllowedKeys(input, [
      "content",
      "direction",
      "correlationId",
      "metadata",
    ]);
    const body: JsonObject = {
      content: input.content,
      direction: input.direction,
      ...(input.correlationId === undefined
        ? {}
        : { correlation_id: input.correlationId }),
      ...(input.metadata === undefined ? {} : { metadata: input.metadata }),
    };
    const result = await this.#transport.request("POST", "/api/v1/analyze", {
      body,
      route: "/api/v1/analyze",
      ...options,
    });
    return parseAnalyze(result.data, requestId(result.response.headers));
  }
}

function incidentQuery(
  filters: IncidentFilters | undefined,
  cursor: string | undefined,
  limit: number,
): URLSearchParams {
  if (limit < 1 || limit > 100)
    throw new RangeError("limit must be between 1 and 100");
  const query = new URLSearchParams({ limit: String(limit) });
  if (cursor !== undefined) query.set("cursor", cursor);
  for (const status of filters?.status ?? []) query.append("status", status);
  for (const severity of filters?.severity ?? [])
    query.append("severity", severity);
  const scalar: Record<string, string | undefined> = {
    application_id: filters?.applicationId,
    environment_id: filters?.environmentId,
    assignee_user_id: filters?.assigneeUserId,
    source: filters?.source,
    action: filters?.action,
    category: filters?.category,
    from: filters?.from,
    to: filters?.to,
    search: filters?.search,
  };
  for (const [key, value] of Object.entries(scalar))
    if (value !== undefined) query.set(key, value);
  if (filters?.unassigned === true) query.set("unassigned", "true");
  return query;
}

export class RenzaiSession {
  readonly #transport: Transport;
  readonly #csrfToken: string;

  constructor(options: RenzaiSessionOptions) {
    assertAllowedKeys(options, [
      "sessionToken",
      "csrfToken",
      "baseUrl",
      "cookieName",
      "timeoutMs",
      "retry",
      "fetch",
      "logger",
    ]);
    const cookieName = options.cookieName ?? "__Host-renzai_session";
    const sessionToken = headerSafe(options.sessionToken, "sessionToken");
    if (sessionToken.includes(";"))
      throw new TypeError("sessionToken must be cookie-safe");
    this.#csrfToken = headerSafe(options.csrfToken, "csrfToken");
    this.#transport = new Transport({
      baseUrl: options.baseUrl,
      headers: { Cookie: `${cookieName}=${sessionToken}` },
      ...(options.timeoutMs === undefined
        ? {}
        : { timeoutMs: options.timeoutMs }),
      ...(options.retry === undefined ? {} : { retry: options.retry }),
      ...(options.fetch === undefined ? {} : { fetch: options.fetch }),
      ...(options.logger === undefined ? {} : { logger: options.logger }),
    });
  }

  toString(): string {
    return `RenzaiSession(baseUrl=${JSON.stringify(this.#transport.baseUrl)})`;
  }

  async listIncidents(
    organizationId: string,
    input: { filters?: IncidentFilters; cursor?: string; limit?: number } = {},
    options: RequestOptions = {},
  ): Promise<IncidentPage> {
    const result = await this.#transport.request(
      "GET",
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/incidents`,
      {
        query: incidentQuery(input.filters, input.cursor, input.limit ?? 50),
        route: "/api/v1/organizations/{organization_id}/incidents",
        ...options,
      },
    );
    return parseIncidentPage(result.data, requestId(result.response.headers));
  }

  async *iterIncidents(
    organizationId: string,
    input: {
      filters?: IncidentFilters;
      pageSize?: number;
      maxPages?: number;
    } = {},
    options: RequestOptions = {},
  ): AsyncGenerator<Incident> {
    const maxPages = input.maxPages ?? 100;
    if (maxPages < 1 || maxPages > 1000)
      throw new RangeError("maxPages must be between 1 and 1000");
    const seen = new Set<string>();
    let cursor: string | undefined;
    for (let pageNumber = 0; pageNumber < maxPages; pageNumber += 1) {
      const page = await this.listIncidents(
        organizationId,
        {
          ...(input.filters === undefined ? {} : { filters: input.filters }),
          ...(cursor === undefined ? {} : { cursor }),
          limit: input.pageSize ?? 50,
        },
        options,
      );
      for (const incident of page.items) yield incident;
      if (page.nextCursor === null) return;
      if (seen.has(page.nextCursor)) {
        throw new RenzaiProtocolError("Renzai repeated a pagination cursor.", {
          code: "protocol_error",
        });
      }
      seen.add(page.nextCursor);
      cursor = page.nextCursor;
    }
    throw new RenzaiProtocolError("Incident pagination exceeded maxPages.", {
      code: "protocol_error",
    });
  }

  async getIncident(
    organizationId: string,
    incidentId: string,
    options: RequestOptions = {},
  ): Promise<Incident> {
    const result = await this.#transport.request(
      "GET",
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/incidents/${encodeURIComponent(incidentId)}`,
      {
        route:
          "/api/v1/organizations/{organization_id}/incidents/{incident_id}",
        ...options,
      },
    );
    return parseIncident(result.data);
  }

  async updateIncidentStatus(
    organizationId: string,
    incidentId: string,
    input: { status: IncidentStatus; version: number; reason?: string },
    options: RequestOptions = {},
  ): Promise<Incident> {
    const result = await this.#write(
      "PATCH",
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/incidents/${encodeURIComponent(incidentId)}/status`,
      {
        status: input.status,
        version: input.version,
        ...(input.reason === undefined ? {} : { reason: input.reason }),
      },
      "/api/v1/organizations/{organization_id}/incidents/{incident_id}/status",
      options,
    );
    return parseIncident(result.data);
  }

  async assignIncident(
    organizationId: string,
    incidentId: string,
    input: { assigneeUserId: string | null; version: number },
    options: RequestOptions = {},
  ): Promise<Incident> {
    const result = await this.#write(
      "PATCH",
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/incidents/${encodeURIComponent(incidentId)}/assignment`,
      { assignee_user_id: input.assigneeUserId, version: input.version },
      "/api/v1/organizations/{organization_id}/incidents/{incident_id}/assignment",
      options,
    );
    return parseIncident(result.data);
  }

  async addIncidentComment(
    organizationId: string,
    incidentId: string,
    body: string,
    options: RequestOptions = {},
  ): Promise<JsonObject> {
    const result = await this.#write(
      "POST",
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/incidents/${encodeURIComponent(incidentId)}/comments`,
      { body },
      "/api/v1/organizations/{organization_id}/incidents/{incident_id}/comments",
      options,
    );
    return asObject(result.data, "incident comment");
  }

  async analytics(
    organizationId: string,
    input: {
      window?: "24h" | "7d" | "30d" | "90d";
      applicationId?: string;
      environmentId?: string;
      source?: "analyze" | "playground" | "gateway";
    } = {},
    options: RequestOptions = {},
  ): Promise<AnalyticsDashboard> {
    const query = new URLSearchParams({ window: input.window ?? "24h" });
    if (input.applicationId !== undefined)
      query.set("application_id", input.applicationId);
    if (input.environmentId !== undefined)
      query.set("environment_id", input.environmentId);
    if (input.source !== undefined) query.set("source", input.source);
    const result = await this.#transport.request(
      "GET",
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/analytics/dashboard`,
      {
        query,
        route: "/api/v1/organizations/{organization_id}/analytics/dashboard",
        ...options,
      },
    );
    return parseAnalytics(result.data, requestId(result.response.headers));
  }

  async requestAI(
    organizationId: string,
    incidentId: string,
    input: {
      taskType: AITaskType;
      disclosureMode?: DisclosureMode;
      idempotencyKey?: string;
    },
    options: RequestOptions = {},
  ): Promise<AIIntelligenceResult> {
    const result = await this.#write(
      "POST",
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/incidents/${encodeURIComponent(incidentId)}/ai-analysis`,
      {
        task_type: input.taskType,
        disclosure_mode: input.disclosureMode ?? "redacted",
      },
      "/api/v1/organizations/{organization_id}/incidents/{incident_id}/ai-analysis",
      options,
      input.idempotencyKey === undefined
        ? undefined
        : { "Idempotency-Key": input.idempotencyKey },
    );
    return parseAI(result.data, requestId(result.response.headers));
  }

  async listAI(
    organizationId: string,
    incidentId: string,
    options: RequestOptions = {},
  ): Promise<AIIntelligenceResult[]> {
    const result = await this.#transport.request(
      "GET",
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/incidents/${encodeURIComponent(incidentId)}/ai-analysis`,
      {
        route:
          "/api/v1/organizations/{organization_id}/incidents/{incident_id}/ai-analysis",
        ...options,
      },
    );
    const data = asObject(result.data, "AI intelligence list");
    if (!Array.isArray(data.items))
      throw new RenzaiProtocolError("Renzai returned a malformed AI list.", {
        code: "protocol_error",
      });
    return data.items.map((item) =>
      parseAI(item, requestId(result.response.headers)),
    );
  }

  async getAI(
    organizationId: string,
    aiRequestId: string,
    options: RequestOptions = {},
  ): Promise<AIIntelligenceResult> {
    const result = await this.#transport.request(
      "GET",
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/ai-analysis/${encodeURIComponent(aiRequestId)}`,
      {
        route:
          "/api/v1/organizations/{organization_id}/ai-analysis/{request_id}",
        ...options,
      },
    );
    return parseAI(result.data, requestId(result.response.headers));
  }

  async #write(
    method: "POST" | "PATCH",
    path: string,
    body: JsonObject,
    route: string,
    options: RequestOptions,
    headers: Record<string, string> = {},
  ): Promise<{ data: unknown; response: Response }> {
    return this.#transport.request(method, path, {
      body,
      route,
      headers: { "X-Renzai-CSRF": this.#csrfToken, ...headers },
      ...options,
    });
  }
}
