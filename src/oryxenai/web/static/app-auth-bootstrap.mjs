import {
  clearPrivateState,
  createBrowserAuth,
  getBrowserStorage,
  logoutCurrentBrowser,
  readAuthConfig,
  resolveAuthenticatedContext,
  safeRelativePath,
} from "../../auth/static/auth-runtime.mjs";

function replace(location, destination) {
  if (location?.pathname !== destination) location?.replace?.(destination);
}

function showBootstrapError(documentRef, message) {
  let node = documentRef?.getElementById?.("auth-bootstrap-error");
  if (!node && documentRef?.createElement) {
    node = documentRef.createElement("p");
    node.id = "auth-bootstrap-error";
    node.setAttribute("role", "alert");
    node.className = "error-text";
    documentRef.querySelector("main")?.prepend(node);
  }
  if (node) node.textContent = message;
}

export async function bootProductShell({
  auth,
  fetchImpl = globalThis.fetch,
  location = globalThis.location,
  storage = getBrowserStorage(globalThis),
  config = readAuthConfig(globalThis.document),
  globalRef = globalThis,
  loadWorkspace = async () => {
    await import("/static/app.js");
    return globalRef?.OryxenAIApp;
  },
} = {}) {
  const paths = config.paths || {};
  const signIn = safeRelativePath(paths.signIn || "/sign-in", "/sign-in");
  const access = safeRelativePath(paths.access || "/access-not-approved", "/access-not-approved");
  const unavailable = safeRelativePath(
    paths.unavailable || "/account-unavailable",
    "/account-unavailable",
  );
  const onboarding = safeRelativePath(paths.onboarding || "/onboarding", "/onboarding");
  const appPath = safeRelativePath(paths.app || "/app", "/app");
  const isDeveloperPage = location?.pathname === "/dev";
  let appController = null;
  const onAuthFailure = async () => {
    appController?.stop?.();
    clearPrivateState(storage);
    replace(location, signIn);
  };

  try {
    auth ||= createBrowserAuth(config, globalRef).auth;
  } catch (error) {
    showBootstrapError(globalRef.document, "Authentication is not configured for this application.");
    replace(location, signIn);
    return { kind: "config_error", error };
  }

  const context = await resolveAuthenticatedContext({
    auth,
    fetchImpl,
    location,
    storage,
    onAuthFailure,
  });
  if (context.kind === "signed_out" || context.kind === "storage_error") {
    if (context.kind === "storage_error") {
      showBootstrapError(
        globalRef.document,
        "This browser could not restore secure auth storage. Please allow site storage and retry.",
      );
    }
    replace(location, signIn);
    return context;
  }
  if (context.kind === "access_not_approved") {
    replace(location, access);
    return context;
  }
  if (context.kind === "account_unavailable") {
    replace(location, unavailable);
    return context;
  }
  if (context.kind !== "authenticated") {
    replace(location, signIn);
    return context;
  }

  if (context.me?.onboarding_required) {
    replace(location, onboarding);
    return { ...context, kind: "onboarding" };
  }
  if (isDeveloperPage && context.me?.role !== "admin") {
    replace(location, appPath);
    return { ...context, kind: "not_admin" };
  }

  appController = await loadWorkspace();
  if (!appController?.boot) {
    await onAuthFailure();
    return { kind: "workspace_error" };
  }
  appController.boot({
    authorizedFetch: context.authorizedFetch,
    storage,
    me: context.me,
    role: context.me.role,
    developer: isDeveloperPage,
  });

  const logout = globalRef.document?.getElementById?.("app-logout");
  logout?.addEventListener("click", async () => {
    logout.disabled = true;
    await logoutCurrentBrowser({
      auth,
      storage,
      location,
      stopActivity: () => appController?.stop?.(),
    });
  });
  const adminLink = globalRef.document?.getElementById?.("app-admin-link");
  if (adminLink) adminLink.hidden = context.me.role !== "admin";
  return { ...context, kind: isDeveloperPage ? "developer" : "app" };
}

if (typeof document !== "undefined") {
  bootProductShell().catch(() => {
    showBootstrapError(document, "Authentication could not be initialized.");
  });
}
