function replace(location, destination) {
  if (location?.pathname !== destination) location?.replace?.(destination);
}

function hideBootstrapProgress(documentRef) {
  const progress = documentRef?.getElementById?.("auth-bootstrap-progress");
  if (progress) progress.hidden = true;
  progress?.setAttribute?.("aria-hidden", "true");
}

function showBootstrapError(documentRef, message) {
  let node = documentRef?.getElementById?.("auth-bootstrap-error");
  if (!node && documentRef?.createElement) {
    node = documentRef.createElement("p");
    node.id = "auth-bootstrap-error";
    node.setAttribute("role", "alert");
    node.className = "error-text start-error";
    const parent = documentRef.querySelector?.("main") || documentRef.body;
    parent?.prepend?.(node);
  }
  if (node) node.textContent = message;
  hideBootstrapProgress(documentRef);
}

function revealWorkspace(documentRef) {
  hideBootstrapProgress(documentRef);
  documentRef?.body?.classList?.remove?.("auth-pending");
}

function renderTemporaryDashboard(documentRef, me) {
  documentRef?.querySelectorAll?.('[data-user="username"]').forEach((element) => {
    element.textContent = me?.username || "there";
  });
  documentRef?.querySelectorAll?.('[data-user="role"]').forEach((element) => {
    element.textContent = me?.role || "—";
  });
  documentRef?.querySelectorAll?.('[data-user="status"]').forEach((element) => {
    element.textContent = me?.status || "—";
  });
  const capabilities = documentRef?.getElementById?.("portfolio-capabilities");
  const state = documentRef?.getElementById?.("workspace-state");
  const policy = me?.policy;
  if (capabilities && policy) {
    capabilities.hidden = false;
    const set = (name, value) => {
      const element = capabilities.querySelector(`[data-entitlement="${name}"]`);
      if (element) element.textContent = value;
    };
    set("policy", policy === "unlimited_admin" ? "unlimited admin" : "single portfolio");
    set("generation", me.read_only ? "promoted success" : me.generation_run_id ? "one variant bound" : "available");
    set("mode", me.read_only ? "read-only" : "mutable");
  }
  if (state) {
    state.textContent = me?.read_only
      ? "A verified success is complete. This portfolio is now read-only."
      : me?.can_start_generation === false && me?.generation_run_id
        ? "Your one generation variant is in progress. Retry is controlled by the server."
        : "No protected product data was loaded before authentication and /me verification.";
  }
}

export async function bootProductShell({
  auth,
  fetchImpl = globalThis.fetch,
  location = globalThis.location,
  storage,
  config,
  globalRef = globalThis,
  timeoutMs,
  loadWorkspace = async () => {
    // /product_shell.html renders this meta tag only when the Preact bundle
    // (frontend/, docs/Frontend/05) has actually been built. The legacy
    // static workspace was retired; never silently load a second UI.
    const entry = globalRef?.document
      ?.querySelector?.('meta[name="oryxenai-product-entry"]')
      ?.content;
    if (!entry) throw new Error("The Preact product bundle is unavailable.");
    return import(entry);
  },
} = {}) {
  // Keep the bootstrap module itself loadable even if the auth runtime alias
  // is unavailable. A static top-level import would reject before the outer
  // catch below can reveal a recovery state, leaving the HTML progress copy
  // visible forever.
  const {
    canonicalDestination,
    createBrowserAuth,
    getBrowserStorage,
    invalidateBrowserSession,
    logoutCurrentBrowser,
    readAuthConfig,
    resolveAuthenticatedContext,
    safeRelativePath,
  } = await import("../../auth/static/auth-runtime.mjs");
  storage ??= getBrowserStorage(globalRef);
  config ??= readAuthConfig(globalRef.document);
  const paths = config.paths || {};
  const signIn = safeRelativePath(paths.signIn || "/sign-in", "/sign-in");
  const access = safeRelativePath(paths.access || "/access-not-approved", "/access-not-approved");
  const unavailable = safeRelativePath(
    paths.unavailable || "/account-unavailable",
    "/account-unavailable",
  );
  const onboarding = safeRelativePath(paths.onboarding || "/onboarding", "/onboarding");
  const appPath = safeRelativePath(paths.app || "/app", "/app");
  const isWorkspacePage = location?.pathname === appPath;
  let appController = null;
  const onAuthFailure = async () => {
    await invalidateBrowserSession({
      auth,
      storage,
      stopActivity: () => appController?.stop?.(),
    });
    replace(location, signIn);
  };

  const canonical = canonicalDestination(config, location);
  if (canonical) {
    location?.replace?.(canonical);
    return { kind: "canonical_redirect" };
  }

  if (config?.pipelineMode === "detached") {
    const appController = await loadWorkspace();
    if (!appController?.boot) {
      showBootstrapError(globalRef.document, "The workspace could not be initialized.");
      return { kind: "workspace_error" };
    }
    const defaultMe = {
      id: "detached-user",
      username: "developer",
      role: "admin",
      status: "active",
      onboarding_required: false,
      admin_available: true,
      read_only: false,
      portfolio_session_id: null,
    };
    appController.boot({
      authorizedFetch: fetchImpl,
      storage,
      pipelineMode: "detached",
      developer: true,
      role: "admin",
      me: defaultMe,
      serverSessionId: null,
      readOnly: false,
    });
    revealWorkspace(globalRef.document);
    return { kind: "detached" };
  }

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
    timeoutMs,
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
  if (context.kind === "auth_timeout") {
    showBootstrapError(
      globalRef.document,
      "Authentication is taking longer than expected. Check your connection and refresh to try again.",
    );
    revealWorkspace(globalRef.document);
    return context;
  }
  if (context.kind === "provider_unavailable" || context.kind === "provider_credit_exhausted") {
    // Transient provider/credit conditions are not an invalid session. Stay
    // on the current page, keep the session, and show a safe message instead
    // of signing the user out (the bug this corrects: see
    // docs/Frontend/06-cross-model-review-and-decisions.md §3.2).
    showBootstrapError(
      globalRef.document,
      context.kind === "provider_credit_exhausted"
        ? "Generation is temporarily unavailable. Retry this same run later."
        : "Authentication is temporarily unavailable. Please try again shortly.",
    );
    revealWorkspace(globalRef.document);
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
  if (isWorkspacePage) {
    try {
      appController = await loadWorkspace();
    } catch (error) {
      showBootstrapError(
        globalRef.document,
        "Your session is active, but the workspace could not be loaded. Refresh to try again.",
      );
      revealWorkspace(globalRef.document);
      return { ...context, kind: "workspace_error", error };
    }
    if (!appController?.boot) {
      showBootstrapError(
        globalRef.document,
        "Your session is active, but the workspace could not be initialized. Refresh to try again.",
      );
      revealWorkspace(globalRef.document);
      return { ...context, kind: "workspace_error" };
    }
    appController.boot({
      authorizedFetch: context.authorizedFetch,
      storage,
      me: context.me,
      role: context.me.role,
      developer: false,
      serverSessionId: context.me.portfolio_session_id || null,
      readOnly: Boolean(context.me.read_only),
    });
  }

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
  revealWorkspace(globalRef.document);
  return { ...context, kind: "app" };
}

if (typeof document !== "undefined") {
  bootProductShell().catch(() => {
    showBootstrapError(document, "Authentication could not be initialized.");
    revealWorkspace(document);
  });
}
