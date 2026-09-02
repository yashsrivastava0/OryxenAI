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

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId: string | null;

  constructor(message: string, options: { code: string; status: number; requestId?: string | null }) {
    super(message);
    this.name = "ApiError";
    this.code = options.code;
    this.status = options.status;
    this.requestId = options.requestId ?? null;
  }
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
  GENERATION_VARIANT_LOCKED: "Your one Code Generator variant is already bound. Retry that run if the server allows it.",
  PORTFOLIO_READ_ONLY: "This portfolio has a verified success and is now read-only.",
  MODEL_PROVIDER_CREDIT_EXHAUSTED: "Generation is temporarily unavailable. Retry this same run later.",
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
  return new ApiError(message, { code, status: response.status, requestId });
}
