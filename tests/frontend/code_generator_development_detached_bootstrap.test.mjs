import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  createAnonymousRequest,
} from "../../src/oryxenai/web/static/code-generator-development-detached-bootstrap.mjs";

test("detached bootstrap strips bearer auth and keeps requests same-origin", async () => {
  const calls = [];
  const request = createAnonymousRequest(async (url, init) => {
    calls.push({ url, init });
    return { ok: true };
  });

  await request("/api/v1/development/code-generator/readiness", {
    headers: { Authorization: "Bearer should-not-cross-boundary", "X-Debug": "1" },
  });

  assert.equal(calls[0].init.credentials, "same-origin");
  assert.equal(calls[0].init.cache, "no-store");
  assert.equal(calls[0].init.headers.get("Authorization"), null);
  assert.equal(calls[0].init.headers.get("X-Debug"), "1");
});

test("detached bootstrap contains no auth or session module dependency", async () => {
  const source = await readFile(
    new URL("../../src/oryxenai/web/static/code-generator-development-detached-bootstrap.mjs", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(source, /auth-client|dev-auth-bootstrap|supabase/i);
});
