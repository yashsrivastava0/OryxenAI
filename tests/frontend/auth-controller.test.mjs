import assert from "node:assert/strict";
import test from "node:test";

import {
  createAuthorizedFetch,
  isReviewedDestination,
  logoutCurrentBrowser,
  routeController,
} from "../../src/oryxenai/auth/static/auth-controller.mjs";

function fakeLocation(path, query = "") {
  return {
    pathname: path,
    href: `http://test${path}${query}`,
    replacements: [],
    replace(value) {
      this.replacements.push(value);
    },
  };
}

function response(status, body = {}) {
  return {
    status,
    ok: status >= 200 && status < 300,
    async json() {
      return body;
    },
  };
}

function uiProbe() {
  return {
    panels: [],
    errors: [],
    users: [],
    progressSteps: [],
    panel(value) { this.panels.push(value); },
    error(value) { this.errors.push(value); },
    user(value) { this.users.push(value); },
    progress(step) { this.progressSteps.push(step); },
    clearPrivate() { this.cleared = true; },
  };
}

function authWithSession(session = { access_token: "access-token" }) {
  return {
    getSessionCalls: 0,
    async getSession() {
      this.getSessionCalls += 1;
      return { data: { session } };
    },
    async refreshSession() { return { data: { session } }; },
    async exchangeCodeForSession() { this.exchanged = true; return { data: { session } }; },
  };
}

test("reviewed destinations reject absolute, encoded, foreign, and unknown routes", () => {
  assert.equal(isReviewedDestination("/app"), true);
  assert.equal(isReviewedDestination("/admin"), true);
  assert.equal(isReviewedDestination("https://evil.example/app"), false);
  assert.equal(isReviewedDestination("//evil.example/app"), false);
  assert.equal(isReviewedDestination("/app?next=/admin"), false);
  assert.equal(isReviewedDestination("/%61pp"), false);
  assert.equal(isReviewedDestination("/unknown"), false);
});

test("signed-out first visit does not call a protected API", async () => {
  const location = fakeLocation("/");
  const ui = uiProbe();
  const auth = authWithSession(null);
  let fetchCalls = 0;
  const result = await routeController({
    auth,
    fetchImpl: async () => { fetchCalls += 1; return response(200); },
    location,
    history: { replaceState() {} },
    storage: { removeItem() {} },
    ui,
  });
  assert.equal(result.kind, "signed_out");
  assert.equal(fetchCalls, 0);
  assert.deepEqual(location.replacements, ["/sign-in"]);
});

test("persistent active session resolves /me once and reaches the app", async () => {
  const location = fakeLocation("/app");
  const ui = uiProbe();
  const auth = authWithSession();
  const calls = [];
  const result = await routeController({
    auth,
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return response(200, { id: "local-id", username: "chosen-name", role: "user", status: "active", onboarding_required: false, admin_available: false });
    },
    location,
    history: { replaceState() {} },
    storage: { removeItem() {} },
    ui,
  });
  assert.equal(result.kind, "app");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "/api/v1/me");
  assert.equal(calls[0].init.headers.get("Authorization"), "Bearer access-token");
  assert.deepEqual(location.replacements, []);
  assert.equal(ui.users[0].username, "chosen-name");
});

test("callback exchanges PKCE code, strips artifacts, and progresses to onboarding", async () => {
  const location = fakeLocation("/auth/callback", "?code=oauth-code&state=opaque&sb_flow_id=flow-1");
  const historyCalls = [];
  const auth = authWithSession();
  const ui = uiProbe();
  const result = await routeController({
    auth,
    fetchImpl: async () => response(200, { id: "local-id", username: null, role: "user", status: "active", onboarding_required: true, admin_available: false }),
    location,
    history: { replaceState(...args) { historyCalls.push(args); } },
    storage: { removeItem() {} },
    ui,
  });
  assert.equal(result.kind, "onboarding");
  assert.equal(auth.exchanged, true);
  assert.deepEqual(historyCalls[0].slice(1), ["", "/auth/callback"]);
  assert.deepEqual(location.replacements, ["/onboarding"]);
  assert.ok(ui.progressSteps.includes("google"));
});

test("canceled callback clears local state and does not call protected APIs", async () => {
  const location = fakeLocation("/auth/callback", "?error=access_denied&state=opaque");
  const ui = uiProbe();
  let fetchCalls = 0;
  const result = await routeController({
    auth: authWithSession(),
    fetchImpl: async () => { fetchCalls += 1; return response(200); },
    location,
    history: { replaceState() {} },
    storage: { removeItem() {} },
    ui,
  });
  assert.equal(result.kind, "signed_out");
  assert.equal(fetchCalls, 0);
  assert.deepEqual(location.replacements, ["/sign-in"]);
  assert.ok(ui.errors.length > 0);
});

test("unapproved identity goes to the safe access screen", async () => {
  const location = fakeLocation("/sign-in");
  const ui = uiProbe();
  const result = await routeController({
    auth: authWithSession(),
    fetchImpl: async () => response(403, { error: { code: "ACCESS_NOT_APPROVED" } }),
    location,
    history: { replaceState() {} },
    storage: { removeItem() {} },
    ui,
  });
  assert.equal(result.kind, "access_not_approved");
  assert.ok(ui.panels.includes("access"));
  assert.deepEqual(location.replacements, ["/access-not-approved"]);
});

test("normal user requesting admin is replaced with app, while admin remains", async () => {
  const normalLocation = fakeLocation("/admin");
  const common = { history: { replaceState() {} }, storage: { removeItem() {} } };
  const normal = await routeController({
    ...common,
    auth: authWithSession(),
    fetchImpl: async () => response(200, { id: "a", username: "normal", role: "user", status: "active", onboarding_required: false, admin_available: false }),
    location: normalLocation,
    ui: uiProbe(),
  });
  assert.equal(normal.kind, "app");
  assert.deepEqual(normalLocation.replacements, ["/app"]);

  const adminLocation = fakeLocation("/admin");
  const admin = await routeController({
    ...common,
    auth: authWithSession(),
    fetchImpl: async () => response(200, { id: "b", username: "admin-user", role: "admin", status: "active", onboarding_required: false, admin_available: true }),
    location: adminLocation,
    ui: uiProbe(),
  });
  assert.equal(admin.kind, "admin");
  assert.deepEqual(adminLocation.replacements, []);
});

test("unsafe configured destinations fall back to reviewed local routes", async () => {
  const location = fakeLocation("/admin");
  const result = await routeController({
    auth: authWithSession(),
    fetchImpl: async () => response(200, { id: "a", username: "normal", role: "user", status: "active", onboarding_required: false, admin_available: false }),
    location,
    history: { replaceState() {} },
    storage: { removeItem() {} },
    paths: { app: "https://evil.example/steal", admin: "//evil.example/admin" },
    ui: uiProbe(),
  });
  assert.equal(result.kind, "app");
  assert.deepEqual(location.replacements, ["/app"]);
});

test("one 401 refreshes once and retries; a failed refresh clears private state", async () => {
  let calls = 0;
  let refreshes = 0;
  const auth = {
    async getSession() { return { data: { session: { access_token: "old" } } }; },
    async refreshSession() { refreshes += 1; return { data: { session: { access_token: "new" } } }; },
  };
  const request = createAuthorizedFetch({ auth, fetchImpl: async (_url, init) => {
    calls += 1;
    return calls === 1 ? response(401) : response(200, { ok: true, authorization: init.headers.get("Authorization") });
  } });
  const ok = await request("/api/v1/me");
  assert.equal((await ok.json()).authorization, "Bearer new");
  assert.equal(calls, 2);
  assert.equal(refreshes, 1);

  let failureClears = 0;
  const badAuth = {
    async getSession() { return { data: { session: { access_token: "old" } } }; },
    async refreshSession() { return { data: { session: null }, error: new Error("expired") }; },
  };
  await assert.rejects(
    createAuthorizedFetch({ auth: badAuth, fetchImpl: async () => response(401), onAuthFailure: async () => { failureClears += 1; } })("/api/v1/me"),
    { code: "AUTH_INVALID" },
  );
  assert.equal(failureClears, 1);
});

test("logout stops activity, clears private UI, signs out, and replaces the page", async () => {
  const location = fakeLocation("/app");
  const ui = uiProbe();
  let stopped = 0;
  let signedOut = 0;
  const storage = { removed: [], removeItem(key) { this.removed.push(key); } };
  await logoutCurrentBrowser({
    auth: { async signOut() { signedOut += 1; throw new Error("provider unavailable"); } },
    storage,
    ui,
    location,
    stopActivity: () => { stopped += 1; },
  });
  assert.equal(stopped, 1);
  assert.equal(signedOut, 1);
  assert.equal(ui.cleared, true);
  assert.deepEqual(storage.removed, [
    "oryxenai.session_id",
    "oryxenai.discovery.session",
    "oryxenai.private",
  ]);
  assert.deepEqual(location.replacements, ["/sign-in"]);
});
