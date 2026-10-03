import assert from "node:assert/strict";
import test from "node:test";

import { bootProductShell } from "../../src/oryxenai/web/static/app-auth-bootstrap.mjs";

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
    reloadCalls: 0,
    replace(value) { this.replacements.push(value); },
    reload() { this.reloadCalls += 1; },
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
  const main = {
    children: [],
    prepend(node) {
      node.parentNode = this;
      this.children.unshift(node);
    },
    append(node) {
      node.parentNode = this;
      this.children.push(node);
    },
    insertAfter(node, reference) {
      const index = this.children.indexOf(reference);
      node.parentNode = this;
      this.children.splice(index + 1, 0, node);
    },
  };
  const createElement = (tagName) => ({
    tagName: tagName.toUpperCase(),
    attributes: {},
    listeners: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(name, callback) { this.listeners[name] = callback; },
    after(node) { this.parentNode?.insertAfter(node, this); },
    click() {
      this.listeners.click?.();
      this.onclick?.();
    },
    textContent: "",
  });
  const progress = {
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
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
      if (id === "auth-bootstrap-progress") return progress;
      return main.children.find((node) => node.id === id) || null;
    },
    createElement,
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
  const documentRef = documentProbe();
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
    globalRef: { document: documentRef },
  });

  assert.equal(result.kind, "app");
  assert.equal(auth.getSessionCalls, 1);
  assert.deepEqual(calls, [{ url: "/api/v1/me", authorization: "Bearer access-token" }]);
  assert.equal(workspaceLoads, 1);
  assert.equal(documentRef.progress.hidden, true);
  assert.equal(documentRef.progress.attributes["aria-hidden"], "true");
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

test("a transient provider 503 is retried and the product workspace opens", async () => {
  const page = location("/app");
  const auth = sessionAuth();
  const sleeps = [];
  let calls = 0;
  let signOutCalls = 0;
  auth.signOut = async () => { signOutCalls += 1; };
  const result = await bootProductShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    sleepImpl: async (milliseconds) => { sleeps.push(milliseconds); },
    fetchImpl: async () => {
      calls += 1;
      if (calls === 1) {
        return response(503, { error: { code: "AUTH_PROVIDER_UNAVAILABLE", message: "down" } });
      }
      return response(200, {
        id: "app-user",
        username: "chosen-name",
        role: "user",
        status: "active",
        onboarding_required: false,
        admin_available: false,
      });
    },
    loadWorkspace: async () => ({ boot() {} }),
  });

  assert.equal(result.kind, "app");
  assert.equal(calls, 2);
  assert.deepEqual(sleeps, [1000]);
  assert.equal(signOutCalls, 0);
  assert.deepEqual(page.replacements, []);
});

test("persistent provider 503 shows Retry and keeps the browser session", async () => {
  const page = location("/app");
  const documentRef = documentProbe();
  const auth = sessionAuth();
  const sleeps = [];
  let calls = 0;
  let signOutCalls = 0;
  auth.signOut = async () => { signOutCalls += 1; };
  const result = await bootProductShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    globalRef: { document: documentRef },
    sleepImpl: async (milliseconds) => { sleeps.push(milliseconds); },
    fetchImpl: async () => {
      calls += 1;
      return response(503, { error: { code: "AUTH_PROVIDER_UNAVAILABLE", message: "down" } });
    },
    loadWorkspace: async () => { throw new Error("workspace must not load"); },
  });

  assert.equal(result.kind, "provider_unavailable");
  assert.equal(calls, 3);
  assert.deepEqual(sleeps, [1000, 2500]);
  assert.equal(signOutCalls, 0);
  assert.deepEqual(page.replacements, []);
  assert.equal(documentRef.main.children[0].textContent, "Authentication is temporarily unavailable. Please try again shortly.");
  assert.equal(documentRef.main.children[1].textContent, "Retry");
  documentRef.main.children[1].click();
  assert.equal(page.reloadCalls, 1);
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

test("a stalled session restore reveals a recoverable error instead of hanging", async () => {
  const page = location("/app");
  const documentRef = documentProbe();
  const auth = {
    async getSession() { return new Promise(() => {}); },
  };

  const result = await bootProductShell({
    auth,
    config,
    location: page,
    storage: { removeItem() {} },
    timeoutMs: 5,
    globalRef: { document: documentRef },
    loadWorkspace: async () => { throw new Error("workspace must not load"); },
  });

  assert.equal(result.kind, "auth_timeout");
  assert.deepEqual(page.replacements, []);
  assert.equal(documentRef.progress.hidden, true);
  assert.equal(documentRef.progress.attributes["aria-hidden"], "true");
  assert.deepEqual(documentRef.body.classList.removed, ["auth-pending"]);
  assert.equal(
    documentRef.main.children[0].textContent,
    "Authentication is taking longer than expected. Check your connection and refresh to try again.",
  );
  assert.equal(documentRef.main.children[1].textContent, "Retry");
});
