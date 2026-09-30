export type RenzaiErrorEnvelope = {
  error: { code: string; message: string; request_id: string; details?: Record<string, unknown> };
};

export class RenzaiApiError extends Error {
  readonly code: string;
  readonly requestId: string;
  readonly details?: Record<string, unknown>;

  constructor(envelope: RenzaiErrorEnvelope) {
    super(envelope.error.message);
    this.name = "RenzaiApiError";
    this.code = envelope.error.code;
    this.requestId = envelope.error.request_id;
    this.details = envelope.error.details;
  }
}

function isRenzaiErrorEnvelope(value: unknown): value is RenzaiErrorEnvelope {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof value.error === "object" &&
    value.error !== null &&
    "code" in value.error &&
    "message" in value.error &&
    "request_id" in value.error
  );
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  csrfToken?: string,
): Promise<T> {
  const requestId = crypto.randomUUID();
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      "X-Request-ID": requestId,
      ...(csrfToken ? { "X-Renzai-CSRF": csrfToken } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    if (isRenzaiErrorEnvelope(body)) throw new RenzaiApiError(body);
    throw new Error(`Unexpected API response (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
