// Direct browser bootstrap for the temporary anonymous pipeline.

const PRIVATE_KEYS = [
  "oryxenai.session_id",
  "oryxenai.discovery.session",
  "oryxenai.private",
];
const PIPELINE_SESSION_KEY = "oryxenai.pipeline.session_id";
const PENDING_RESTART_KEY = "oryxenai.pipeline.pending_restart_session_id";

function storageFor(globalRef) {
  try {
    return globalRef?.sessionStorage || null;
  } catch {
    return null;
  }
}

function clearLegacyStorage(storage) {
  if (!storage) return;
  for (const key of PRIVATE_KEYS) {
    try { storage.removeItem(key); } catch { /* storage is best effort */ }
  }
}

function reveal(documentRef) {
  documentRef?.body?.classList?.remove?.("auth-pending");
}

function showError(documentRef, message) {
  const progress = documentRef?.getElementById?.("auth-bootstrap-progress");
  if (progress) {
    progress.setAttribute("role", "alert");
    progress.replaceChildren(message);
  }
}

export function createDetachedFetch(fetchImpl = globalThis.fetch) {
  return async (input, init = {}) => {
    const headers = new Headers(init.headers || {});
    headers.set("Accept", "application/json");
    headers.set("Cache-Control", "no-store");
    headers.delete("Authorization");
    return fetchImpl(input, {
      ...init,
      headers,
      cache: "no-store",
      credentials: "same-origin",
    });
  };
}

export async function bootDetachedProductShell({
  fetchImpl = globalThis.fetch,
  globalRef = globalThis,
  loadWorkspace = async () => {
    const entry = globalRef?.document
      ?.querySelector?.('meta[name="oryxenai-product-entry"]')
      ?.content;
    if (entry) return import(entry);
    await import("/static/app.js");
    return globalRef?.OryxenAIApp;
  },
} = {}) {
  const storage = storageFor(globalRef);
  clearLegacyStorage(storage);
  const appController = await loadWorkspace();
  if (!appController?.boot) {
    showError(globalRef.document, "The workspace could not be initialized. Refresh to try again.");
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
    authorizedFetch: createDetachedFetch(fetchImpl),
    storage,
    pipelineMode: "detached",
    developer: false,
    role: "admin",
    me: defaultMe,
    serverSessionId: null,
    readOnly: false,
  });
  reveal(globalRef.document);
  globalRef.addEventListener?.("pageshow", (event) => {
    if (event?.persisted) globalRef.location?.reload?.();
  });
  return { kind: "detached" };
}

if (typeof document !== "undefined") {
  bootDetachedProductShell().catch((err) => {
    console.error("bootDetachedProductShell error:", err);
    showError(document, "The development pipeline could not be initialized. Refresh to try again.");
  });
}
