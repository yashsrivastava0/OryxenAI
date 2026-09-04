import assert from "node:assert/strict";
import test from "node:test";

import {
  bootDetachedProductShell,
  createDetachedFetch,
} from "../../src/oryxenai/web/static/pipeline-bootstrap.mjs";

test("detached fetch never sends bearer credentials and disables HTTP caching", async () => {
  let request = null;
  const fetch = createDetachedFetch(async (url, init) => {
    request = { url, init };
    return { ok: true, status: 200 };
  });

  await fetch("/api/v1/sessions", {
    headers: { Authorization: "Bearer stale-token", "X-Test": "ok" },
  });

  assert.equal(request.url, "/api/v1/sessions");
  assert.equal(request.init.cache, "no-store");
  assert.equal(request.init.credentials, "same-origin");
  assert.equal(request.init.headers.get("Authorization"), null);
  assert.equal(request.init.headers.get("Cache-Control"), "no-store");
  assert.equal(request.init.headers.get("X-Test"), "ok");
});

test("detached bootstrap clears legacy browser keys and boots the workspace directly", async () => {
  const values = new Map([
    ["oryxenai.session_id", "old-account-session"],
    ["oryxenai.discovery.session", "old-chat-cache"],
    ["oryxenai.private", "old-private-state"],
  ]);
  const storage = {
    removeItem(key) { values.delete(key); },
    getItem(key) { return values.get(key) || null; },
    setItem(key, value) { values.set(key, value); },
  };
  const documentRef = {
    body: { classList: { remove() {} } },
    getElementById() { return null; },
  };
  let bootOptions = null;
  let fetchCalls = 0;
  const globalRef = {
    sessionStorage: storage,
    document: documentRef,
    addEventListener() {},
  };

  const result = await bootDetachedProductShell({
    globalRef,
    fetchImpl: async () => { fetchCalls += 1; return { ok: true }; },
    loadWorkspace: async () => ({ boot(options) { bootOptions = options; } }),
  });

  assert.equal(result.kind, "detached");
  assert.equal(fetchCalls, 0);
  assert.equal(values.has("oryxenai.session_id"), false);
  assert.equal(values.has("oryxenai.discovery.session"), false);
  assert.equal(values.has("oryxenai.private"), false);
  assert.equal(bootOptions.pipelineMode, "detached");
  assert.equal(bootOptions.me.id, "detached-user");
  assert.equal(bootOptions.me.role, "admin");
  assert.equal(typeof bootOptions.authorizedFetch, "function");
});
