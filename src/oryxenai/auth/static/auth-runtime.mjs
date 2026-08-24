/**
 * Side-effect-free browser auth runtime shared by product and developer
 * shells.  It owns Supabase session access, bearer injection, the single 401
 * refresh boundary, and private browser-state cleanup.
 */

export const REVIEWED_DESTINATIONS = Object.freeze(["/app", "/admin"]);
export const PRIVATE_SESSION_KEYS = Object.freeze([
  "oryxenai.session_id",
  "oryxenai.discovery.session",
  "oryxenai.private",
]);

export class AuthRequestError extends Error {
  constructor(message, { status = 0, code = "AUTH_INVALID" } = {}) {
    super(message);
    this.name = "AuthRequestError";
    this.status = status;
    this.code = code;
  }
}

export function safeSession(result) {
  return result?.data?.session ?? result?.session ?? null;
}

export function clearPrivateState(storage) {
  try {
    for (const key of PRIVATE_SESSION_KEYS) storage?.removeItem?.(key);
  } catch {
    // Storage errors are reported by the session restore boundary.
  }
}

export async function invalidateBrowserSession({
  auth,
  storage,
  ui = {},
  stopActivity = () => {},
}) {
  stopActivity();
  clearPrivateState(storage);
  ui.clearPrivate?.();
  try {
    await auth?.signOut?.({ scope: "local" });
  } catch {
    // Local application state is already cleared. Navigation remains safe.
  }
}

export function canonicalDestination(config, location) {
  if (!config?.primaryOrigin || !location?.href) return null;
  try {
    const primaryOrigin = new URL(config.primaryOrigin).origin;
    const current = new URL(location.href);
    if (current.origin === primaryOrigin) return null;
    const path = safeRelativePath(current.pathname, "/");
    return `${primaryOrigin}${path}`;
  } catch {
    return null;
  }
}

export function isReviewedDestination(value, origin = "http://localhost") {
  if (typeof value !== "string" || !value || value.includes("\\") || value.includes("%")) {
    return false;
  }
  try {
    const safeOrigin = new URL(origin).origin;
    const parsed = new URL(value, origin);
    return (
      parsed.origin === safeOrigin &&
      !parsed.search &&
      !parsed.hash &&
      REVIEWED_DESTINATIONS.includes(parsed.pathname) &&
      value === parsed.pathname
    );
  } catch {
    return false;
  }
}

export function safeRelativePath(value, fallback) {
  if (typeof value !== "string" || !value || value.includes("\\") || value.includes("%")) {
    return fallback;
  }
  try {
    const parsed = new URL(value, "http://localhost");
    return parsed.origin === "http://localhost" &&
      parsed.pathname === value &&
      !parsed.search &&
      !parsed.hash &&
      value.startsWith("/") &&
      !value.startsWith("//")
      ? value
      : fallback;
  } catch {
    return fallback;
  }
}

function errorMessage(code) {
  switch (code) {
    case "AUTH_REQUIRED":
      return "Authentication is required.";
    case "ACCESS_NOT_APPROVED":
      return "This Google account is not approved for OryxenAI access.";
    case "ACCOUNT_SUSPENDED":
    case "ACCOUNT_DELETED":
      return "This OryxenAI account is currently unavailable.";
    case "USER_CAPACITY_REACHED":
      return "Normal-user access is currently at capacity.";
    case "USERNAME_TAKEN":
      return "That username is already taken.";
    case "GENERATION_VARIANT_LOCKED":
      return "Your one Code Generator variant is already bound. Retry that run if the server allows it.";
    case "PORTFOLIO_READ_ONLY":
      return "This portfolio has a verified success and is now read-only.";
    case "MODEL_PROVIDER_CREDIT_EXHAUSTED":
      return "The model provider has no available credit. Retry this same run later.";
    case "AUTHORIZATION_FENCE_REJECTED":
      return "This operation is no longer authorized. Refresh the workspace before trying again.";
    case "ENTITLEMENT_BINDING_CONFLICT":
      return "The portfolio authorization binding could not be changed safely.";
    case "ONBOARDING_REQUIRED":
      return "Complete username onboarding before using this page.";
    case "AUTH_PROVIDER_UNAVAILABLE":
      return "Authentication is temporarily unavailable. Please try again shortly.";
    case "ADMIN_CONFIRMATION_MISMATCH":
      return "The administrator confirmation did not match the target.";
    case "ADMIN_OPERATION_CONFLICT":
      return "That administrator request key was already used with different input.";
    case "ADMIN_OPERATION_RETRYABLE":
    case "STORAGE_CLEANUP_FAILED":
      return "The administrator operation needs a safe retry.";
    case "AUTH_ADMIN_PROVIDER_UNAVAILABLE":
      return "The identity provider administrator operation is temporarily unavailable.";
    case "AUTH_ADMIN_PROVIDER_RATE_LIMITED":
      return "The identity provider administrator operation is rate limited.";
    case "LAST_ACTIVE_ADMIN_REQUIRED":
      return "At least one active administrator must remain.";
    case "ADMIN_SELF_ACTION_FORBIDDEN":
      return "Administrators cannot perform this action on their own identity.";
    case "PROJECT_RUNNING_WORK_PENDING":
      return "Running portfolio work must finish before cleanup can continue.";
    case "PROJECT_DELETION_PENDING":
      return "This portfolio is being deleted and cannot accept new work.";
    case "ENTITLEMENT_RESET_NOT_APPLICABLE":
      return "This account has no deleted portfolio entitlement to reset.";
    default:
      return "Your authentication session is no longer valid.";
  }
}

export async function responseError(response) {
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  const code = body?.error?.code || (response.status === 401 ? "AUTH_INVALID" : "REQUEST_FAILED");
  return new AuthRequestError(errorMessage(code), { status: response.status, code });
}

export function createAuthorizedFetch({
  auth,
  fetchImpl = globalThis.fetch,
  onAuthFailure = () => {},
  initialSession = undefined,
}) {
  if (typeof fetchImpl !== "function") {
    throw new Error("A fetch implementation is required.");
  }
  let bootstrapSession = initialSession;
  let refreshInFlight = null;
  let lastRefresh = null;

  const requireReviewedApiPath = (url) => {
    const rawPath = typeof url === "string" ? url.split("?", 1)[0] : "";
    if (
      typeof url !== "string" ||
      !url.startsWith("/api/v1/") ||
      url.startsWith("//") ||
      url.includes("\\") ||
      rawPath.includes("%") ||
      url.includes("#")
    ) {
      throw new AuthRequestError("Protected requests must use a reviewed local API path.", {
        code: "AUTH_REQUEST_DESTINATION_INVALID",
      });
    }
    const parsed = new URL(url, "http://localhost");
    if (parsed.origin !== "http://localhost") {
      throw new AuthRequestError("Protected requests must use a reviewed local API path.", {
        code: "AUTH_REQUEST_DESTINATION_INVALID",
      });
    }
  };
  const sessionForRequest = async () => {
    if (bootstrapSession !== undefined) {
      const session = bootstrapSession;
      bootstrapSession = undefined;
      return session;
    }
    const result = await auth.getSession();
    if (result?.error) throw result.error;
    return safeSession(result);
  };
  const refreshFor = async (rejectedToken) => {
    if (lastRefresh?.rejectedToken === rejectedToken) return lastRefresh.session;
    if (!refreshInFlight) {
      refreshInFlight = (async () => {
        const result = await auth.refreshSession();
        const session = result?.error ? null : safeSession(result);
        lastRefresh = { rejectedToken, session };
        return session;
      })().finally(() => { refreshInFlight = null; });
    }
    return refreshInFlight;
  };
  const request = async (url, init = {}, session) => {
    if (!session?.access_token) {
      await onAuthFailure();
      throw new AuthRequestError(errorMessage("AUTH_REQUIRED"), {
        status: 401,
        code: "AUTH_REQUIRED",
      });
    }
    const headers = new Headers(init.headers || {});
    headers.set("Authorization", `Bearer ${session.access_token}`);
    headers.set("Accept", "application/json");
    return fetchImpl(url, { ...init, headers });
  };

  return async (url, init = {}) => {
    requireReviewedApiPath(url);
    let session;
    try {
      session = await sessionForRequest();
    } catch {
      await onAuthFailure();
      throw new AuthRequestError(errorMessage("AUTH_INVALID"), { status: 401 });
    }

    let response = await request(url, init, session);
    if (response.status === 401) {
      const rejectedToken = session?.access_token;
      try {
        session = await refreshFor(rejectedToken);
      } catch {
        session = null;
      }
      if (!session?.access_token) {
        await onAuthFailure();
        throw new AuthRequestError(errorMessage("AUTH_INVALID"), { status: 401 });
      }
      response = await request(url, init, session);
      if (response.status === 401) {
        await onAuthFailure();
        throw new AuthRequestError(errorMessage("AUTH_INVALID"), { status: 401 });
      }
    }
    if (!response.ok) throw await responseError(response);
    return response;
  };
}

export function readAuthConfig(documentRef = globalThis.document) {
  const read = (name) => documentRef?.querySelector?.(`meta[name="${name}"]`)?.content || "";
  return {
    supabaseUrl: read("oryxenai-supabase-url"),
    publishableKey: read("oryxenai-publishable-key"),
    admissionMode: read("oryxenai-admission-mode") || "allowlist",
    primaryOrigin: read("oryxenai-primary-origin"),
    callbackUrl: read("oryxenai-callback-url"),
    paths: {
      signIn: read("oryxenai-sign-in-path") || "/sign-in",
      callback: read("oryxenai-callback-path") || "/auth/callback",
      access: read("oryxenai-access-not-approved-path") || "/access-not-approved",
      unavailable: read("oryxenai-account-unavailable-path") || "/account-unavailable",
      onboarding: read("oryxenai-onboarding-path") || "/onboarding",
      app: read("oryxenai-app-path") || "/app",
      admin: read("oryxenai-admin-path") || "/admin",
    },
  };
}

export function createBrowserAuth(config, globalRef = globalThis) {
  if (!config?.supabaseUrl || !config?.publishableKey) {
    throw new AuthRequestError("Authentication is not configured for this application.", {
      code: "AUTH_CONFIG_INVALID",
    });
  }
  const factory = globalRef?.OryxenAISupabaseClient?.createClient;
  if (typeof factory !== "function") {
    throw new AuthRequestError("Authentication is not configured for this application.", {
      code: "AUTH_CONFIG_INVALID",
    });
  }
  const client = factory(config.supabaseUrl, config.publishableKey, {
    auth: {
      flowType: "pkce",
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: false,
    },
  });
  return {
    client,
    auth: {
      getSession: () => client.auth.getSession(),
      refreshSession: () => client.auth.refreshSession(),
      exchangeCodeForSession: (code, options) => client.auth.exchangeCodeForSession(code, options),
      signOut: (options) => client.auth.signOut(options),
      signInWithOAuth: (options) => client.auth.signInWithOAuth(options),
    },
  };
}

export function getBrowserStorage(globalRef = globalThis) {
  try {
    return globalRef?.sessionStorage || null;
  } catch {
    return null;
  }
}

export async function resolveAuthenticatedContext({
  auth,
  fetchImpl = globalThis.fetch,
  location,
  storage,
  onAuthFailure = () => {},
}) {
  let sessionResult;
  try {
    sessionResult = await auth.getSession();
  } catch {
    return { kind: "storage_error" };
  }
  if (sessionResult?.error) return { kind: "storage_error" };
  const session = safeSession(sessionResult);
  if (!session?.access_token) {
    clearPrivateState(storage);
    return { kind: "signed_out" };
  }

  const authorizedFetch = createAuthorizedFetch({
    auth,
    fetchImpl,
    initialSession: session,
    onAuthFailure,
  });
  try {
    const response = await authorizedFetch("/api/v1/me", { method: "GET" });
    const me = await response.json();
    return { kind: "authenticated", me, session, authorizedFetch };
  } catch (error) {
    if (error instanceof AuthRequestError) {
      if (error.code === "ACCESS_NOT_APPROVED" || error.code === "USER_CAPACITY_REACHED") {
        return { kind: "access_not_approved", error };
      }
      if (error.code === "ACCOUNT_SUSPENDED" || error.code === "ACCOUNT_DELETED") {
        return { kind: "account_unavailable", error };
      }
      if (error.code === "ONBOARDING_REQUIRED") return { kind: "onboarding", error };
    }
    await onAuthFailure();
    return { kind: "auth_failure", error };
  }
}

export async function logoutCurrentBrowser({
  auth,
  storage,
  ui = {},
  location,
  signInPath = "/sign-in",
  stopActivity = () => {},
}) {
  await invalidateBrowserSession({ auth, storage, ui, stopActivity });
  location?.replace?.(safeRelativePath(signInPath, "/sign-in"));
}
