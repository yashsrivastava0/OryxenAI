/**
 * Small deterministic auth controller.
 *
 * The exported functions intentionally accept their browser dependencies so
 * Node's built-in test runner can exercise redirects, refresh, and logout
 * without a DOM, Supabase, Google, or network access.
 */

import {
  AuthRequestError,
  clearPrivateState,
  createAuthorizedFetch,
  isReviewedDestination,
  logoutCurrentBrowser,
  responseError,
  safeRelativePath,
  safeSession,
} from "./auth-runtime.mjs";

export {
  AuthRequestError,
  createAuthorizedFetch,
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
    if (location?.pathname !== destination) location?.replace?.(destination);
  };
  const progress = (step, detail) => ui.progress?.(step, detail);
  const failure = (message) => ui.error?.(message);
  const onAuthFailure = async () => {
    stopActivity();
    clearPrivateState(storage);
    ui.clearPrivate?.();
    replace(reviewed.signIn);
  };

  progress("restore", "Restoring your session.");
  if (path === reviewed.callback) {
    const currentUrl = new URL(location?.href || `http://localhost${path}`);
    const params = currentUrl.searchParams;
    stripOAuthArtifacts(history, location);
    if (params.get("error") || params.get("error_code")) {
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
        const exchanged = await auth.exchangeCodeForSession(code, options);
        if (exchanged?.error) throw exchanged.error;
      } catch {
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
    sessionResult = await auth.getSession();
  } catch {
    ui.panel?.("sign-in");
    failure("This browser could not restore its secure auth storage. Please allow site storage and retry.");
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
    const response = await authorizedFetch("/api/v1/me", { method: "GET" });
    me = await response.json();
  } catch (error) {
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
        failure(error.message);
        replace(reviewed.signIn);
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
    replace(reviewed.app);
    return { kind: "app", me };
  }
  if (path === reviewed.admin && me.role === "admin" && me.admin_available) {
    ui.panel?.("admin");
    replace(reviewed.admin);
    return { kind: "admin", me };
  }
  ui.panel?.("app");
  replace(reviewed.app);
  return { kind: "app", me };
}

function readMeta(name) {
  return document.querySelector(`meta[name="${name}"]`)?.content || "";
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
    Object.entries(panels).forEach(([key, element]) => {
      if (element) element.hidden = key !== name;
    });
    root?.focus({ preventScroll: true });
  };
  return {
    progress(step, detail) {
      show("controller");
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
    error(message) {
      const error = document.getElementById("global-error");
      if (error) {
        error.textContent = message;
        error.hidden = !message;
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
  const config = {
    supabaseUrl: readMeta("oryxenai-supabase-url"),
    publishableKey: readMeta("oryxenai-publishable-key"),
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
  if (!config.supabaseUrl || !config.publishableKey || !window.OryxenAISupabaseClient) {
    ui.panel("sign-in");
    ui.error("Authentication is not configured for this application.");
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
    signOut: () => client.auth.signOut(),
    signInWithOAuth: (options) => client.auth.signInWithOAuth(options),
  };
  const storage = (() => { try { return window.sessionStorage; } catch { return null; } })();
  const result = await routeController({
    auth,
    location: window.location,
    history: window.history,
    storage,
    ui,
    paths: config.paths,
  });
  if (result?.kind === "admin") {
    const { bootstrapAdminConsole } = await import("./auth-admin.mjs");
    await bootstrapAdminConsole({ auth });
  }
  const signIn = document.getElementById("google-sign-in");
  signIn?.addEventListener("click", async () => {
    signIn.disabled = true;
    ui.error("");
    try {
      const response = await auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: config.callbackUrl },
      });
      if (response?.error) throw response.error;
    } catch {
      signIn.disabled = false;
      ui.error("Google sign-in could not start. Please try again shortly.");
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
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("username");
    const submit = form.querySelector('button[type="submit"]');
    const error = document.getElementById("username-error");
    if (!input?.value || !submit) return;
    submit.disabled = true;
    if (error) { error.hidden = true; error.textContent = ""; }
    try {
      const authorizedFetch = createAuthorizedFetch({
        auth,
        onAuthFailure: async () => { clearPrivateState(storage); ui.clearPrivate(); },
      });
      const response = await authorizedFetch("/api/v1/me/username", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: input.value }),
      });
      if (!response.ok) throw await responseError(response);
      window.location.replace(config.paths.app);
    } catch (caught) {
      if (error) {
        error.textContent = caught instanceof AuthRequestError ? caught.message : "Username could not be claimed.";
        error.hidden = false;
      }
      submit.disabled = false;
    }
  });
  if (result?.kind === "onboarding") document.getElementById("username")?.focus();
}
