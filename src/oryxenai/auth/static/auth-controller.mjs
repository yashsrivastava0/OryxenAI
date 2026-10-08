/**
 * Small deterministic auth controller.
 *
 * The exported functions intentionally accept their browser dependencies so
 * Node's built-in test runner can exercise redirects, refresh, and logout
 * without a DOM, Supabase, Google, or network access.
 */

import { consumePrivateDestination } from "./return-route.mjs";
import {
  AUTH_BOOTSTRAP_TIMEOUT_MS,
  AuthBootstrapTimeoutError,
  AuthRequestError,
  canonicalDestination,
  clearPrivateState,
  createAuthorizedFetch,
  fetchAuthenticatedUser,
  invalidateBrowserSession,
  isReviewedDestination,
  logoutCurrentBrowser,
  responseError,
  safeRelativePath,
  safeSession,
  withTimeout,
} from "./auth-runtime.mjs";

export {
  AuthBootstrapTimeoutError,
  AuthRequestError,
  canonicalDestination,
  createAuthorizedFetch,
  fetchAuthenticatedUser,
  isReviewedDestination,
  logoutCurrentBrowser,
};

export function stripOAuthArtifacts(history, location) {
  const path = location?.pathname || "/auth/callback";
  history?.replaceState?.({}, "", path);
  return path;
}

export async function routeController({
  auth,
  fetchImpl = globalThis.fetch,
  location,
  history,
  storage,
  ui = {},
  paths = {},
  path = location?.pathname || "/",
  stopActivity = () => {},
  timeoutMs = AUTH_BOOTSTRAP_TIMEOUT_MS,
  sleepImpl,
}) {
  const reviewed = {
    signIn: safeRelativePath(paths.signIn || "/sign-in", "/sign-in"),
    callback: safeRelativePath(paths.callback || "/auth/callback", "/auth/callback"),
    access: safeRelativePath(paths.access || "/access-not-approved", "/access-not-approved"),
    unavailable: safeRelativePath(
      paths.unavailable || "/account-unavailable",
      "/account-unavailable",
    ),
    onboarding: safeRelativePath(paths.onboarding || "/onboarding", "/onboarding"),
    app: isReviewedDestination(paths.app || "/app") ? paths.app || "/app" : "/app",
    admin: isReviewedDestination(paths.admin || "/admin") ? paths.admin || "/admin" : "/admin",
  };
  const replace = (destination) => {
    if (path === "/" && destination === reviewed.signIn && location?.href) {
      const url = new URL(location.href);
      const sample = url.searchParams.get("sample");
      if (["daybreak", "nightshift", "velvet"].includes(sample)) {
        destination += `?sample=${sample}${url.hash === "#sign-in-panel" ? url.hash : ""}`;
      }
    }
    if (location?.pathname !== destination) location?.replace?.(destination);
  };
  const progress = (step, detail) => ui.progress?.(step, detail);
  const failure = (message, options) => ui.error?.(message, options);
  const rememberCallbackFailure = (kind) => {
    try { storage?.setItem?.("oryxenai.auth_notice", kind); } catch { /* Site storage may be unavailable. */ }
  };
  const onAuthFailure = async () => {
    await invalidateBrowserSession({ auth, storage, ui, stopActivity });
    replace(reviewed.signIn);
  };

  progress("restore", "Restoring your session.");
  if (path === reviewed.callback) {
    const currentUrl = new URL(location?.href || `http://localhost${path}`);
    const params = currentUrl.searchParams;
    stripOAuthArtifacts(history, location);
    if (params.get("error") || params.get("error_code")) {
      rememberCallbackFailure("callback_error");
      clearPrivateState(storage);
      ui.panel?.("sign-in");
      failure("Google sign-in was canceled or could not be completed.");
      replace(reviewed.signIn);
      return { kind: "signed_out", reason: "callback_error" };
    }
    const code = params.get("code");
    if (code) {
      progress("google", "Completing Google sign-in.");
      try {
        const flowId = params.get("sb_flow_id");
        const options = flowId ? { flowId } : undefined;
        const exchanged = await withTimeout(auth.exchangeCodeForSession(code, options), timeoutMs);
        if (exchanged?.error) throw exchanged.error;
      } catch {
        rememberCallbackFailure("callback_exchange");
        clearPrivateState(storage);
        ui.panel?.("sign-in");
        failure("Google sign-in could not be completed. Please try again.");
        replace(reviewed.signIn);
        return { kind: "signed_out", reason: "callback_exchange" };
      }
    }
  }

  let sessionResult;
  try {
    sessionResult = await withTimeout(auth.getSession(), timeoutMs);
  } catch (error) {
    ui.panel?.("sign-in");
    failure(error instanceof AuthBootstrapTimeoutError
      ? "Session restoration is taking longer than expected. Please retry."
      : "This browser could not restore its secure auth storage. Please allow site storage and retry.", { retry: true });
    replace(reviewed.signIn);
    return { kind: "storage_error" };
  }
  if (sessionResult?.error) {
    ui.panel?.("sign-in");
    failure("This browser could not restore its secure auth storage. Please allow site storage and retry.");
    replace(reviewed.signIn);
    return { kind: "storage_error" };
  }
  const session = safeSession(sessionResult);
  if (!session?.access_token) {
    stopActivity();
    clearPrivateState(storage);
    ui.clearPrivate?.();
    ui.panel?.("sign-in");
    replace(reviewed.signIn);
    return { kind: "signed_out" };
  }

  progress("verify", "Verifying OryxenAI access.");
  let me;
  try {
    const authorizedFetch = createAuthorizedFetch({ auth, fetchImpl, onAuthFailure });
    me = await fetchAuthenticatedUser({ authorizedFetch, timeoutMs, sleepImpl });
  } catch (error) {
    if (error instanceof AuthBootstrapTimeoutError) {
      ui.panel?.("sign-in");
      failure(
        "Authentication is taking longer than expected. Check your connection and try again.",
        { retry: true },
      );
      return { kind: "provider_unavailable", error };
    }
    if (error instanceof AuthRequestError) {
      if (error.code === "ACCESS_NOT_APPROVED") {
        ui.panel?.("access");
        failure(error.message);
        replace(reviewed.access);
        return { kind: "access_not_approved" };
      }
      if (error.code === "ACCOUNT_SUSPENDED" || error.code === "ACCOUNT_DELETED") {
        ui.panel?.("unavailable");
        failure(error.message);
        replace(reviewed.unavailable);
        return { kind: "account_unavailable" };
      }
      if (error.code === "USER_CAPACITY_REACHED") {
        ui.panel?.("access");
        failure(error.message);
        replace(reviewed.access);
        return { kind: "access_not_approved" };
      }
      if (error.code === "AUTH_PROVIDER_UNAVAILABLE") {
        ui.panel?.("sign-in");
        failure(error.message, { retry: true });
        return { kind: "provider_unavailable" };
      }
      if (error.code === "MODEL_PROVIDER_CREDIT_EXHAUSTED") {
        ui.panel?.("app");
        failure(error.message);
        replace(reviewed.app);
        return { kind: "provider_credit_exhausted" };
      }
    }
    await onAuthFailure();
    return { kind: "auth_failure" };
  }

  progress("workspace", "Preparing your workspace.");
  ui.user?.(me);
  if (me.onboarding_required) {
    ui.panel?.("onboarding");
    replace(reviewed.onboarding);
    return { kind: "onboarding", me };
  }
  if (path === reviewed.onboarding) {
    ui.panel?.("app");
    replace(consumePrivateDestination());
    return { kind: "app", me };
  }
  if (path === reviewed.admin && me.role === "admin" && me.admin_available) {
    ui.panel?.("admin");
    replace(reviewed.admin);
    return { kind: "admin", me };
  }
  ui.panel?.("app");
  replace(consumePrivateDestination());
  return { kind: "app", me };
}

function readMeta(name) {
  return document.querySelector(`meta[name="${name}"]`)?.content || "";
}

function publishAuthOutcome(kind) {
  document.body.dataset.authOutcome = kind;
  window.dispatchEvent(new CustomEvent("oryxenai-auth-resolved", { detail: { kind } }));
}

export function validateUsername(value) {
  const handle = value.trim().toLowerCase();
  return /^[a-z0-9](?:[a-z0-9_-]{1,28})[a-z0-9]$/.test(handle)
    ? "" : "Use 3–30 letters, numbers, underscores or hyphens. Start and end with a letter or number.";
}

function makeDomUi() {
  const root = document.getElementById("auth-root");
  const panels = {
    controller: document.getElementById("progress-panel"),
    "sign-in": document.getElementById("sign-in-panel"),
    access: document.getElementById("access-panel"),
    unavailable: document.getElementById("unavailable-panel"),
    onboarding: document.getElementById("onboarding-panel"),
    app: document.getElementById("app-panel"),
    admin: document.getElementById("admin-panel"),
  };
  const progressSteps = [...document.querySelectorAll("[data-progress-step]")];
  const stepOrder = ["restore", "google", "verify", "workspace"];
  const show = (name) => {
    const alreadyVisible = panels[name] && !panels[name].hidden;
    Object.entries(panels).forEach(([key, element]) => {
      if (element) element.hidden = key !== name;
    });
    if (!alreadyVisible) root?.focus({ preventScroll: true });
  };
  return {
    progress(step, detail) {
      if (!["/", "/sign-in"].includes(window.location.pathname)) show("controller");
      const title = document.getElementById("progress-title");
      const description = document.getElementById("progress-detail");
      const index = stepOrder.indexOf(step);
      if (title) title.textContent = detail;
      if (description) description.textContent = "Your browser session stays on this device.";
      progressSteps.forEach((item) => {
        const itemIndex = stepOrder.indexOf(item.dataset.progressStep);
        item.classList.toggle("current", itemIndex === index);
        item.classList.toggle("complete", itemIndex >= 0 && itemIndex < index);
      });
    },
    panel: show,
    error(message, { retry = false } = {}) {
      const globalError = document.getElementById("global-error");
      const signInError = document.getElementById("sign-in-error");
      const error = panels["sign-in"] && !panels["sign-in"].hidden && signInError ? signInError : globalError;
      for (const other of [globalError, signInError]) {
        if (other && other !== error) { other.hidden = true; other.textContent = ""; }
      }
      if (error) {
        error.textContent = message;
        error.hidden = !message;
      }
      let retryButton = document.getElementById("auth-provider-retry");
      if (retry && !retryButton && error?.parentNode) {
        retryButton = document.createElement("button");
        retryButton.id = "auth-provider-retry";
        retryButton.type = "button";
        retryButton.className = "button button-secondary";
        retryButton.textContent = "Retry";
        error.parentNode.append(retryButton);
      }
      if (retryButton) {
        retryButton.hidden = !retry;
        retryButton.onclick = () => globalThis.location?.reload?.();
      }
    },
    clearPrivate() {
      document.querySelectorAll("[data-user]").forEach((element) => { element.textContent = "—"; });
    },
    user(me) {
      document.querySelectorAll('[data-user="username"]').forEach((element) => { element.textContent = me.username || "there"; });
      document.querySelectorAll('[data-user="role"]').forEach((element) => { element.textContent = me.role || "—"; });
      document.querySelectorAll('[data-user="status"]').forEach((element) => { element.textContent = me.status || "—"; });
      const adminLink = document.getElementById("admin-link");
      if (adminLink) adminLink.hidden = me.role !== "admin" || !me.admin_available;
    },
  };
}

export async function bootstrapAuthPage() {
  if (document.body.dataset.authInitialized) return;
  document.body.dataset.authInitialized = "true";
  const config = {
    supabaseUrl: readMeta("oryxenai-supabase-url"),
    publishableKey: readMeta("oryxenai-publishable-key"),
    admissionMode: readMeta("oryxenai-admission-mode") || "allowlist",
    primaryOrigin: readMeta("oryxenai-primary-origin"),
    callbackUrl: readMeta("oryxenai-callback-url"),
    paths: {
      signIn: readMeta("oryxenai-sign-in-path") || "/sign-in",
      callback: readMeta("oryxenai-callback-path") || "/auth/callback",
      app: readMeta("oryxenai-app-path") || "/app",
      admin: readMeta("oryxenai-admin-path") || "/admin",
      onboarding: readMeta("oryxenai-onboarding-path") || "/onboarding",
      access: readMeta("oryxenai-access-not-approved-path") || "/access-not-approved",
      unavailable: readMeta("oryxenai-account-unavailable-path") || "/account-unavailable",
    },
  };
  const ui = makeDomUi();
  const openAdmission = config.admissionMode === "open";
  const signInGuidance = document.getElementById("sign-in-guidance");
  if (signInGuidance) {
    signInGuidance.textContent = "Use your Google account to get started.";
  }
  const accessDetail = document.getElementById("access-detail");
  if (accessDetail && openAdmission) {
    accessDetail.textContent =
      "The 15 normal-user slots may be full, or this Google identity is not yet available from the provider.";
  }
  const canonical = canonicalDestination(config, window.location);
  if (canonical) {
    window.location.replace(canonical);
    return;
  }
  if (!config.supabaseUrl || !config.publishableKey || !window.OryxenAISupabaseClient) {
    ui.panel("sign-in");
    ui.error("Authentication is not configured for this application.", { retry: true });
    document.getElementById("google-sign-in")?.setAttribute("aria-busy", "false");
    const status = document.getElementById("sign-in-status");
    if (status) status.hidden = true;
    publishAuthOutcome("provider_unavailable");
    return;
  }
  const client = window.OryxenAISupabaseClient.createClient(config.supabaseUrl, config.publishableKey, {
    auth: {
      flowType: "pkce",
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: false,
    },
  });
  const auth = {
    getSession: () => client.auth.getSession(),
    refreshSession: () => client.auth.refreshSession(),
    exchangeCodeForSession: (code, options) => client.auth.exchangeCodeForSession(code, options),
    signOut: (options) => client.auth.signOut(options),
    signInWithOAuth: (options) => client.auth.signInWithOAuth(options),
  };
  const storage = (() => { try { return window.sessionStorage; } catch { return null; } })();
  let callbackNotice = null;
  if (window.location.pathname === config.paths.signIn) {
    try {
      callbackNotice = storage?.getItem("oryxenai.auth_notice");
      storage?.removeItem("oryxenai.auth_notice");
    } catch { /* Authentication reports unavailable browser storage separately. */ }
  }
  const result = await routeController({
    auth,
    location: window.location,
    history: window.history,
    storage,
    ui,
    paths: config.paths,
  });
  publishAuthOutcome(result.kind);
  if (result.kind === "signed_out" && ["callback_error", "callback_exchange"].includes(callbackNotice)) {
    ui.error(callbackNotice === "callback_error"
      ? "Google sign-in was canceled or could not be completed."
      : "Google sign-in could not be completed. Please try again.");
  }
  const status = document.getElementById("sign-in-status");
  if (status) status.hidden = true;
  if (result?.kind === "admin") {
    const { bootstrapAdminConsole } = await import("./auth-admin.mjs");
    await bootstrapAdminConsole({ auth, me: result.me });
  }
  const signIn = document.getElementById("google-sign-in");
  let oauthPending = false;
  const resetSignInCta = () => {
    if (!signIn || oauthPending) return;
    signIn.disabled = false;
    signIn.setAttribute("aria-busy", "false");
    signIn.classList.remove("cta-submitting");
    const label = signIn.querySelector(".cta-label");
    if (label) {
      label.textContent = "Continue with Google";
    }
  };
  resetSignInCta();

  window.addEventListener("pageshow", resetSignInCta);
  window.addEventListener("focus", resetSignInCta);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      resetSignInCta();
    }
  });

  signIn?.addEventListener("click", async () => {
    if (oauthPending || signIn.disabled) return;
    oauthPending = true;
    signIn.disabled = true;
    signIn.setAttribute("aria-busy", "true");
    signIn.classList.add("cta-submitting");
    const label = signIn.querySelector(".cta-label");
    if (label) label.textContent = "Opening Google…";
    ui.error("");
    try {
      const response = await withTimeout(auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: config.callbackUrl,
          skipBrowserRedirect: true,
          // Always let the user choose which Google identity to use. Without
          // this, Google may silently reuse the account from the previous
          // OryxenAI session after local sign-out.
          queryParams: { prompt: "select_account" },
        },
      }), AUTH_BOOTSTRAP_TIMEOUT_MS);
      if (response?.error) throw response.error;
      const destination = new URL(response?.data?.url);
      if (destination.origin !== new URL(config.supabaseUrl).origin) throw new Error("Unexpected sign-in destination");
      window.location.assign(destination.href);
    } catch {
      oauthPending = false;
      resetSignInCta();
      ui.error("Google sign-in could not start. Please try again shortly.");
    } finally {
      oauthPending = false;
    }
  });
  document.querySelectorAll('[data-action="logout"]').forEach((button) => {
    button.addEventListener("click", async () => {
      document.querySelectorAll("button").forEach((item) => { item.disabled = true; });
      await logoutCurrentBrowser({
        auth,
        storage,
        ui,
        location: window.location,
        signInPath: config.paths.signIn,
      });
    });
  });
  const form = document.getElementById("username-form");
  document.getElementById("username")?.addEventListener("input", (event) => {
    const error = document.getElementById("username-error");
    const message = validateUsername(event.target.value);
    if (error) { error.textContent = message; error.hidden = !message; }
    event.target.setAttribute("aria-invalid", String(Boolean(message)));
  });
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("username");
    const submit = form.querySelector('button[type="submit"]');
    const error = document.getElementById("username-error");
    if (!input?.value || !submit || submit.disabled) return;
    const invalid = validateUsername(input.value);
    if (invalid) {
      if (error) { error.textContent = invalid; error.hidden = false; }
      input.focus();
      return;
    }
    const originalLabel = submit.textContent;
    submit.disabled = true;
    submit.textContent = "Saving your handle…";
    if (error) { error.hidden = true; error.textContent = ""; }
    try {
      const authorizedFetch = createAuthorizedFetch({
        auth,
        onAuthFailure: async () => {
          await invalidateBrowserSession({ auth, storage, ui });
          window.location.replace(config.paths.signIn);
        },
      });
      const response = await withTimeout(authorizedFetch("/api/v1/me/username", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: input.value }),
      }), AUTH_BOOTSTRAP_TIMEOUT_MS);
      if (!response.ok) throw await responseError(response);
      window.location.replace(consumePrivateDestination(window));
    } catch (caught) {
      if (error) {
        error.textContent = caught instanceof AuthRequestError ? caught.message : "Username could not be claimed.";
        error.hidden = false;
      }
      submit.disabled = false;
      submit.textContent = originalLabel;
    }
  });
  if (result?.kind === "onboarding") document.getElementById("username")?.focus();
}
