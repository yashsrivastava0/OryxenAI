import assert from "node:assert/strict";
import test from "node:test";

import { adminEndpoint, bootstrapAdminConsole } from "../../src/oryxenai/auth/static/auth-admin.mjs";

test("administrator actions use reviewed server endpoints", () => {
  assert.equal(
    adminEndpoint("readmit", "deleted", "identity-1"),
    "/api/v1/admin/deleted-identities/identity-1/readmit",
  );
  assert.equal(
    adminEndpoint("reset_entitlement", "users", "user-1"),
    "/api/v1/admin/users/user-1/entitlement/reset",
  );
  assert.equal(
    adminEndpoint("code-generator-regenerate", "projects", "project-1"),
    "/api/v1/admin/projects/project-1/code-generator/regenerate",
  );
  assert.equal(
    adminEndpoint("delete", "legacy", "project-1"),
    "/api/v1/admin/legacy-projects/project-1/delete",
  );
});

test("admin module performs no protected fetch outside the admin panel", async () => {
  let calls = 0;
  await bootstrapAdminConsole({
    auth: {},
    fetchImpl: async () => {
      calls += 1;
      throw new Error("unexpected protected request");
    },
    documentRef: { getElementById: () => null },
  });
  assert.equal(calls, 0);
});
