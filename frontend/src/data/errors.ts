// Error envelope handling shared by every product API call. Mirrors the
// error-code catalog and safe-message rules in
// docs/Frontend/05-implementation-blueprint-and-acceptance-matrix.md §4.7 and
// §10.2 — deliberately its own module (not shared with
// src/oryxenai/auth/static/auth-runtime.mjs) because auth errors are handled
// before this bundle ever loads; this module only sees already-authenticated
// product API calls.

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
}

export interface ApiErrorDetails {
  provider_label?: string;
  operation_label?: string;
  retry_after_seconds?: number;
  support_reference?: string;
  retryable?: boolean;
}

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId: string | null;
  readonly providerLabel: string | null;
  readonly operationLabel: string | null;
  readonly retryAfterSeconds: number | null;
  readonly supportReference: string | null;

  constructor(
    message: string,
    options: {
      code: string;
      status: number;
      requestId?: string | null;
      details?: ApiErrorDetails | null;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.code = options.code;
    this.status = options.status;
    this.requestId = options.requestId ?? null;
    this.providerLabel = options.details?.provider_label ?? null;
    this.operationLabel = options.details?.operation_label ?? null;
    this.retryAfterSeconds = options.details?.retry_after_seconds ?? null;
    this.supportReference = options.details?.support_reference ?? null;
  }
}

function readSafeDetails(value: unknown): ApiErrorDetails | null {
  if (typeof value !== "object" || value === null) return null;
  const raw = value as Record<string, unknown>;
  const result: ApiErrorDetails = {};
  if (
    raw.provider_label === "Experiential Labs" ||
    raw.provider_label === "Google Gemini" ||
    raw.provider_label === "Configured model provider"
  ) {
    result.provider_label = raw.provider_label;
  }
  if (typeof raw.operation_label === "string" && raw.operation_label.trim() && raw.operation_label.length <= 160) {
    result.operation_label = raw.operation_label.trim();
  }
  if (typeof raw.retry_after_seconds === "number" && Number.isFinite(raw.retry_after_seconds) && raw.retry_after_seconds >= 0 && raw.retry_after_seconds <= 86400) {
    result.retry_after_seconds = raw.retry_after_seconds;
  }
  if (typeof raw.support_reference === "string" && /^model-[a-f0-9]{12}$/i.test(raw.support_reference)) {
    result.support_reference = raw.support_reference;
  }
  if (raw.retryable === true) result.retryable = true;
  return Object.keys(result).length ? result : null;
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as { error?: unknown }).error === "object" &&
    (value as ApiErrorEnvelope).error !== null &&
    typeof (value as ApiErrorEnvelope).error.code === "string"
  );
}

// Safe, reviewed product copy for known codes. Falls through to the server's
// own message (already reviewed to be safe) when a code isn't listed here,
// and finally to a generic message. Never surfaces provider names, storage
// vendors, hashes, or stack traces — see docs/Frontend/05 §9 copy system.
const KNOWN_MESSAGES: Record<string, string> = {
  ENTITLEMENT_BINDING_CONFLICT: "The portfolio authorization binding could not be changed safely.",
  AUTHORIZATION_FENCE_REJECTED: "This operation is no longer authorized. Refresh the workspace before trying again.",
  PORTFOLIO_SESSION_STALE: "This portfolio changed in another tab. Refresh to see the latest state.",
};

export async function parseApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  const code = isApiErrorEnvelope(body) ? body.error.code : "REQUEST_FAILED";
  const requestId = isApiErrorEnvelope(body) ? (body.error.request_id ?? null) : null;
  const serverMessage = isApiErrorEnvelope(body) ? body.error.message : null;
  const message = KNOWN_MESSAGES[code] ?? serverMessage ?? "The request could not be completed.";
  const details = isApiErrorEnvelope(body) ? readSafeDetails(body.error.details) : null;
  return new ApiError(message, { code, status: response.status, requestId, details });
}
