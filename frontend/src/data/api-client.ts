// Thin, typed wrapper around the authorizedFetch handed in at boot (see
// src/oryxenai/web/static/app-auth-bootstrap.mjs -> appController.boot()).
// authorizedFetch already owns the bearer-token/401-refresh boundary (see
// src/oryxenai/auth/static/auth-runtime.mjs createAuthorizedFetch) and throws
// on any non-2xx response using its own AuthRequestError — this module
// re-maps that into product-facing ApiError copy (errors.ts) rather than
// re-implementing the fetch boundary.
//
// The authenticated product intentionally ends after Visual Design Director.
// Later stages keep separate development harnesses and are not callable here.

import { ApiError } from "./errors";

export type AuthorizedFetch = (url: string, init?: RequestInit) => Promise<Response>;

interface DuckTypedAuthError {
  code?: unknown;
  status?: unknown;
  message?: unknown;
}

function isDuckTypedAuthError(value: unknown): value is DuckTypedAuthError {
  return typeof value === "object" && value !== null && "code" in value;
}

// authorizedFetch throws before this module ever sees the Response for a
// non-2xx result, so remap its error here rather than in errors.ts.
function remapAuthorizedFetchError(error: unknown): ApiError {
  if (isDuckTypedAuthError(error)) {
    const code = typeof error.code === "string" ? error.code : "REQUEST_FAILED";
    const status = typeof error.status === "number" ? error.status : 0;
    const message = typeof error.message === "string" ? error.message : "The request could not be completed.";
    return new ApiError(message, { code, status });
  }
  return new ApiError("The request could not be completed.", { code: "REQUEST_FAILED", status: 0 });
}

async function requestJson<T>(
  authorizedFetch: AuthorizedFetch,
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await authorizedFetch(path, init);
  } catch (error) {
    throw remapAuthorizedFetchError(error);
  }
  return (await response.json()) as T;
}

function jsonInit(method: string, body?: unknown, idempotencyKey?: string): RequestInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  return { method, headers, body: body === undefined ? undefined : JSON.stringify(body) };
}

// Envelope shape is intentionally loose (docs/Frontend/05 §4.7): adapters
// validate the stage-specific payload defensively, not this client.
export interface CacheReceipt {
  cache_hit?: boolean;
  cached_stage_count?: number;
  stage_count?: number;
  saved_calls?: number;
  run_id?: string;
}

export interface StageEnvelope {
  session_id: string;
  session_revision: number;
  [stageKey: string]: unknown;
}

export interface MeProjection {
  id: string;
  username: string | null;
  role: "user" | "admin";
  status: string;
  onboarding_required: boolean;
  admin_available: boolean;
  read_only?: boolean;
  can_create_portfolio?: boolean;
  portfolio_session_id?: string | null;
  [key: string]: unknown;
}

export function createApiClient(authorizedFetch: AuthorizedFetch) {
  return {
    getMe: () => requestJson<MeProjection>(authorizedFetch, "/api/v1/me"),

    getSession: (sessionId: string) =>
      requestJson<{ id: string; name: string; status: string; current_state: Record<string, unknown>; revision: number }>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}`,
      ),

    createSession: (name?: string) =>
      requestJson<{ id: string; name: string; status: string; revision: number }>(
        authorizedFetch,
        "/api/v1/sessions",
        jsonInit("POST", name ? { name } : {}),
      ),

    getDiscovery: (sessionId: string) =>
      requestJson<StageEnvelope>(authorizedFetch, `/api/v1/sessions/${encodeURIComponent(sessionId)}/discovery`),

    startDiscovery: (
      sessionId: string,
      body: { message?: string; document_text?: string; goal?: string },
      idempotencyKey?: string,
    ) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/discovery/start`,
        jsonInit("POST", body, idempotencyKey),
      ),

    putDiscoveryAnswers: (
      sessionId: string,
      body: { complete: boolean; answers: Array<{ question_id: string; mode: string; value: unknown }> },
    ) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/discovery/answers`,
        jsonInit("PUT", body),
      ),

    reviseDiscovery: (sessionId: string, revisionRequest: string) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/discovery/revise`,
        jsonInit("POST", { revision_request: revisionRequest }),
      ),

    approveDiscovery: (sessionId: string) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/discovery/approve`,
        jsonInit("POST", {}),
      ),

    getContentArchitect: (sessionId: string) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/content-architect`,
      ),

    startContentArchitect: (
      sessionId: string,
      body: { preferences?: Record<string, unknown>; model_profile?: string } = {},
      idempotencyKey?: string,
    ) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/content-architect/start`,
        jsonInit("POST", body, idempotencyKey),
      ),

    reviseContentArchitect: (sessionId: string, revisionRequest: string) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/content-architect/revise`,
        jsonInit("POST", { revision_request: revisionRequest }),
      ),

    approveContentArchitect: (sessionId: string) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/content-architect/approve`,
        jsonInit("POST", {}),
      ),

    getVisualDesignDirector: (sessionId: string) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/visual-design-director`,
      ),

    startVisualDesignDirector: (
      sessionId: string,
      body: { preferences?: Record<string, unknown>; model_profile?: string } = {},
      idempotencyKey?: string,
    ) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/visual-design-director/start`,
        jsonInit("POST", body, idempotencyKey),
      ),

    reviseVisualDesignDirector: (sessionId: string, revisionRequest: string) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/visual-design-director/revise`,
        jsonInit("POST", { revision_request: revisionRequest }),
      ),

    approveVisualDesignDirector: (sessionId: string) =>
      requestJson<StageEnvelope>(
        authorizedFetch,
        `/api/v1/sessions/${encodeURIComponent(sessionId)}/visual-design-director/approve`,
        jsonInit("POST", {}),
      ),

  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
