import {
  RenzaiConnectionError,
  RenzaiProtocolError,
  RenzaiTimeoutError,
} from "./errors.js";
import { requestId, throwServerError } from "./protocol.js";
import type { JsonObject, RequestOptions, RetryPolicy } from "./types.js";

export type SafeLogEvent = {
  method: string;
  route: string;
  status: number;
  requestId?: string;
  durationMs: number;
};

export type TransportOptions = {
  baseUrl: string;
  headers: Record<string, string>;
  timeoutMs?: number;
  retry?: RetryPolicy;
  fetch?: typeof globalThis.fetch;
  logger?: (event: SafeLogEvent) => void;
  maxResponseBytes?: number;
};

type TransportResponse = { data: unknown; response: Response };

function normalizeBaseUrl(value: string): string {
  const parsed = new URL(value);
  if (
    !["http:", "https:"].includes(parsed.protocol) ||
    parsed.username ||
    parsed.password ||
    parsed.search ||
    parsed.hash
  ) {
    throw new TypeError(
      "baseUrl must be an absolute HTTP(S) URL without credentials, query, or fragment",
    );
  }
  return value.replace(/\/$/u, "");
}

function retryPolicy(value: RetryPolicy | undefined): Required<RetryPolicy> {
  const result = {
    maxAttempts: value?.maxAttempts ?? 3,
    initialBackoffMs: value?.initialBackoffMs ?? 250,
    maximumBackoffMs: value?.maximumBackoffMs ?? 2000,
  };
  if (result.maxAttempts < 1 || result.maxAttempts > 5)
    throw new RangeError("maxAttempts must be 1-5");
  if (result.initialBackoffMs < 0 || result.initialBackoffMs > 10_000) {
    throw new RangeError("initialBackoffMs must be 0-10000");
  }
  if (result.maximumBackoffMs < 0 || result.maximumBackoffMs > 30_000) {
    throw new RangeError("maximumBackoffMs must be 0-30000");
  }
  return result;
}

async function readBounded(
  response: Response,
  maximum: number,
): Promise<string> {
  if (response.body === null) return "";
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  for (;;) {
    const next = await reader.read();
    if (next.done) break;
    total += next.value.byteLength;
    if (total > maximum) {
      await reader.cancel();
      const responseRequestId = requestId(response.headers);
      throw new RenzaiProtocolError(
        "Renzai response exceeded the configured size limit.",
        {
          code: "protocol_error",
          ...(responseRequestId === undefined
            ? {}
            : { requestId: responseRequestId }),
          statusCode: response.status,
        },
      );
    }
    chunks.push(next.value);
  }
  const combined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(combined);
}

export class Transport {
  readonly #baseUrl: string;
  readonly #headers: Record<string, string>;
  readonly #timeoutMs: number;
  readonly #retry: Required<RetryPolicy>;
  readonly #fetch: typeof globalThis.fetch;
  readonly #logger: ((event: SafeLogEvent) => void) | undefined;
  readonly #maxResponseBytes: number;

  constructor(options: TransportOptions) {
    this.#baseUrl = normalizeBaseUrl(options.baseUrl);
    this.#headers = {
      "User-Agent": "Renzai-TypeScript/0.1.0",
      Accept: "application/json",
      ...options.headers,
    };
    this.#timeoutMs = options.timeoutMs ?? 30_000;
    if (this.#timeoutMs < 1 || this.#timeoutMs > 300_000)
      throw new RangeError("timeoutMs must be 1-300000");
    this.#retry = retryPolicy(options.retry);
    this.#fetch = options.fetch ?? globalThis.fetch;
    this.#logger = options.logger;
    this.#maxResponseBytes = options.maxResponseBytes ?? 2 * 1024 * 1024;
    if (
      this.#maxResponseBytes < 1 ||
      this.#maxResponseBytes > 20 * 1024 * 1024
    ) {
      throw new RangeError("maxResponseBytes must be between 1 and 20971520");
    }
  }

  get baseUrl(): string {
    return this.#baseUrl;
  }

  async request(
    method: "GET" | "POST" | "PATCH",
    path: string,
    options: RequestOptions & {
      body?: JsonObject;
      query?: URLSearchParams;
      headers?: Record<string, string>;
      route: string;
    },
  ): Promise<TransportResponse> {
    for (let attempt = 1; attempt <= this.#retry.maxAttempts; attempt += 1) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), this.#timeoutMs);
      const signal =
        options.signal === undefined
          ? controller.signal
          : AbortSignal.any([controller.signal, options.signal]);
      const started = performance.now();
      try {
        const response = await this.#fetch(
          `${this.#baseUrl}${path}${options.query === undefined ? "" : `?${options.query.toString()}`}`,
          {
            method,
            headers: {
              ...this.#headers,
              ...(options.body === undefined
                ? {}
                : { "Content-Type": "application/json" }),
              ...options.headers,
            },
            ...(options.body === undefined
              ? {}
              : { body: JSON.stringify(options.body) }),
            signal,
            redirect: "manual",
          },
        );
        const responseRequestId = requestId(response.headers);
        this.#logger?.({
          method,
          route: options.route,
          status: response.status,
          ...(responseRequestId === undefined
            ? {}
            : { requestId: responseRequestId }),
          durationMs: Math.round(performance.now() - started),
        });
        if (
          method === "GET" &&
          response.status === 429 &&
          attempt < this.#retry.maxAttempts
        ) {
          const retryAfter = response.headers.get("Retry-After");
          if (retryAfter !== null && Number.isFinite(Number(retryAfter))) {
            await delay(
              Math.min(
                this.#retry.maximumBackoffMs,
                Math.max(0, Number(retryAfter) * 1000),
              ),
              options.signal,
            );
            continue;
          }
        }
        const text = await readBounded(response, this.#maxResponseBytes);
        let data: unknown;
        try {
          data = JSON.parse(text);
        } catch (error) {
          throw new RenzaiProtocolError(
            "Renzai returned malformed JSON.",
            {
              code: "protocol_error",
              ...(responseRequestId === undefined
                ? {}
                : { requestId: responseRequestId }),
              statusCode: response.status,
            },
            { cause: error },
          );
        }
        if (!response.ok) throwServerError(data, response);
        return { data, response };
      } catch (error) {
        if (options.signal?.aborted === true) throw error;
        if (controller.signal.aborted) {
          throw new RenzaiTimeoutError(
            "The Renzai request timed out.",
            { code: "timeout" },
            { cause: error },
          );
        }
        if (
          method === "GET" &&
          error instanceof TypeError &&
          attempt < this.#retry.maxAttempts
        ) {
          const backoff = Math.min(
            this.#retry.maximumBackoffMs,
            this.#retry.initialBackoffMs * 2 ** (attempt - 1),
          );
          await delay(backoff, options.signal);
          continue;
        }
        if (error instanceof TypeError) {
          throw new RenzaiConnectionError(
            "The Renzai server could not be reached.",
            { code: "connection_error" },
            { cause: error },
          );
        }
        throw error;
      } finally {
        clearTimeout(timeout);
      }
    }
    throw new Error("unreachable");
  }
}

async function delay(
  milliseconds: number,
  signal?: AbortSignal,
): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, milliseconds);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(
          signal.reason instanceof Error
            ? signal.reason
            : new DOMException("The operation was aborted.", "AbortError"),
        );
      },
      { once: true },
    );
  });
}
