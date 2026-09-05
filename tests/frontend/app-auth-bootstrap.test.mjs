import assert from "node:assert/strict";
import test from "node:test";

import { bootProductShell } from "../../src/oryxenai/web/static/app-auth-bootstrap.mjs";
import { bootDevelopmentShell } from "../../src/oryxenai/web/static/dev-auth-bootstrap.mjs";

function response(status, body = {}) {
  return {
    status,
    ok: status >= 200 && status < 300,
    async json() { return body; },
  };
}

function location(path) {
  return {
    pathname: path,
    replacements: [],
    replace(value) { this.replacements.push(value); },
  };
}

const config = {
  supabaseUrl: "https://project.supabase.co",
  publishableKey: "sb_publishable_test",
  callbackUrl: "http://localhost:8000/auth/callback",
  paths: {
    signIn: "/sign-in",
    access: "/access-not-approved",
    unavailable: "/account-unavailable",
    onboarding: "/onboarding",
    app: "/app",
    admin: "/admin",
  },
};

function sessionAuth(session = { access_token: "access-token" }) {
  return {
    getSessionCalls: 0,
    async getSession() {
      this.getSessionCalls += 1;
      return { data: { session } };
    },
    async refreshSession() { return { data: { session } }; },
  };
}

function documentProbe() {
  const progress = {
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
  };
  const main = {
    children: [],
    prepend(node) { this.children.unshift(node); },
  };
  const body = {
    classList: {
      removed: [],
      remove(name) { this.removed.push(name); },
    },
  };
  return {
    main,
    body,
    progress,
    getElementById(id) {
      return id === "auth-bootstrap-progress" ? progress : null;
    },
    createElement() {
      return {
        setAttribute() {},
        textContent: "",
      };
    },
    querySelector(selector) { return selector === "main" ? main : null; },
  };
}

test("signed-out product visit performs no protected fetch and routes to sign-in", async () => {
  const page = location("/app");
  const auth = sessionAuth(null);
  let protectedCalls = 0;
  const result = await bootProductShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    fetchImpl: async () => { protectedCalls += 1; return response(200); },
    loadWorkspace: async () => { throw new Error("workspace must not load"); },
  });

  assert.equal(result.kind, "signed_out");
  assert.equal(protectedCalls, 0);
  assert.deepEqual(page.replacements, ["/sign-in"]);
});

test("persistent session resolves /me once before loading the product workspace", async () => {
  const page = location("/app");
  const auth = sessionAuth();
  const calls = [];
  let workspaceLoads = 0;
  const result = await bootProductShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    fetchImpl: async (url, init) => {
      calls.push({ url, authorization: init.headers.get("Authorization") });
      return response(200, {
        id: "app-user",
        username: "chosen-name",
        role: "user",
        status: "active",
        onboarding_required: false,
        admin_available: false,
      });
    },
    loadWorkspace: async () => {
      workspaceLoads += 1;
      return { boot() {} };
    },
  });

  assert.equal(result.kind, "app");
  assert.equal(auth.getSessionCalls, 1);
  assert.deepEqual(calls, [{ url: "/api/v1/me", authorization: "Bearer access-token" }]);
  assert.equal(workspaceLoads, 1);
});

test("workspace bootstrap failure preserves a valid auth session and avoids a redirect loop", async () => {
  const page = location("/app");
  const auth = sessionAuth();
  const documentRef = documentProbe();
  let signOutCalls = 0;
  auth.signOut = async () => { signOutCalls += 1; };
  const result = await bootProductShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    fetchImpl: async () => response(200, {
      id: "app-user",
      username: "chosen-name",
      role: "user",
      status: "active",
      onboarding_required: false,
      admin_available: false,
    }),
    loadWorkspace: async () => ({}),
    globalRef: { document: documentRef },
  });

  assert.equal(result.kind, "workspace_error");
  assert.equal(signOutCalls, 0);
  assert.deepEqual(page.replacements, []);
  assert.equal(documentRef.main.children[0].textContent, "Your session is active, but the workspace could not be initialized. Refresh to try again.");
  assert.equal(documentRef.progress.attributes["aria-hidden"], "true");
  assert.deepEqual(documentRef.body.classList.removed, ["auth-pending"]);
});

test("a transient provider outage keeps the session instead of signing out", async () => {
  const page = location("/app");
  const auth = sessionAuth();
  let signOutCalls = 0;
  auth.signOut = async () => { signOutCalls += 1; };
  const result = await bootProductShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    fetchImpl: async () => response(503, { error: { code: "AUTH_PROVIDER_UNAVAILABLE", message: "down" } }),
    loadWorkspace: async () => { throw new Error("workspace must not load"); },
  });

  assert.equal(result.kind, "provider_unavailable");
  assert.equal(signOutCalls, 0);
  assert.deepEqual(page.replacements, []);
});

test("exhausted generation credit keeps the session instead of signing out", async () => {
  const page = location("/app");
  const auth = sessionAuth();
  let signOutCalls = 0;
  auth.signOut = async () => { signOutCalls += 1; };
  const result = await bootProductShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    fetchImpl: async () => response(503, { error: { code: "MODEL_PROVIDER_CREDIT_EXHAUSTED", message: "no credit" } }),
    loadWorkspace: async () => { throw new Error("workspace must not load"); },
  });

  assert.equal(result.kind, "provider_credit_exhausted");
  assert.equal(signOutCalls, 0);
  assert.deepEqual(page.replacements, []);
});

test("normal users cannot initialize a developer shell", async () => {
  const page = location("/dev");
  const auth = sessionAuth();
  let protectedPageLoads = 0;
  const result = await bootProductShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    fetchImpl: async () => response(200, {
      id: "app-user",
      username: "normal",
      role: "user",
      status: "active",
      onboarding_required: false,
      admin_available: false,
    }),
    loadWorkspace: async () => {
      protectedPageLoads += 1;
      return { boot() {} };
    },
  });

  assert.equal(result.kind, "not_admin");
  assert.deepEqual(page.replacements, ["/app"]);
  assert.equal(protectedPageLoads, 0);
});

test("admin developer boot resolves /me before loading the protected page", async () => {
  const page = location("/code-generator-development");
  const auth = sessionAuth();
  const calls = [];
  let loadedTarget = null;
  let loadedRequest = null;
  const result = await bootDevelopmentShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    fetchImpl: async (url, init) => {
      calls.push({ url, authorization: init.headers.get("Authorization") });
      return response(200, {
        id: "admin-user",
        username: "admin-name",
        role: "admin",
        status: "active",
        onboarding_required: false,
        admin_available: true,
      });
    },
    loadProtected: async (target, request) => {
      loadedTarget = target;
      loadedRequest = request;
    },
  });

  assert.equal(result.kind, "development");
  assert.deepEqual(calls, [{ url: "/api/v1/me", authorization: "Bearer access-token" }]);
  assert.equal(loadedTarget, "code-generator");
  assert.equal(typeof loadedRequest, "function");
});

test("detached Build Preparation boot skips auth and uses the anonymous request boundary", async () => {
  const page = location("/build-preparation-fixture");
  let authCalls = 0;
  let loadedTarget = null;
  let loadedRequest = null;
  const result = await bootDevelopmentShell({
    config: { ...config, pipelineMode: "detached" },
    location: page,
    fetchImpl: async (url, init) => {
      authCalls += 1;
      return response(200, { url, cache: init.cache, authorization: init.headers.get("Authorization") });
    },
    loadProtected: async (target, request) => {
      loadedTarget = target;
      loadedRequest = request;
    },
  });

  assert.equal(result.kind, "detached");
  assert.equal(result.target, "fixture");
  assert.equal(authCalls, 0);
  assert.equal(loadedTarget, "fixture");
  const responseValue = await loadedRequest("/api/v1/build-preparation/fixture/preflight");
  assert.equal(responseValue.status, 200);
});
