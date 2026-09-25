import assert from "node:assert/strict";
import test from "node:test";

import {
  adminEndpoint,
  adminSubmissionState,
  bootstrapAdminConsole,
} from "../../src/oryxenai/auth/static/auth-admin.mjs";

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
    adminEndpoint("delete", "legacy", "project-1"),
    "/api/v1/admin/legacy-projects/project-1/delete",
  );
  assert.equal(
    adminEndpoint("resume", "operations", "operation-1"),
    "/api/v1/admin/operations/operation-1/resume",
  );
  assert.equal(
    adminEndpoint("suspend", "users", "user-1"),
    "/api/v1/admin/users/user-1/suspend",
  );
  assert.equal(
    adminEndpoint("restore", "users", "user-1"),
    "/api/v1/admin/users/user-1/restore",
  );
  assert.equal(
    adminEndpoint("promote", "users", "user-1"),
    "/api/v1/admin/users/user-1/promote",
  );
  assert.equal(
    adminEndpoint("demote", "users", "user-1"),
    "/api/v1/admin/users/user-1/demote",
  );
  assert.equal(
    adminEndpoint("delete", "users", "user-1"),
    "/api/v1/admin/users/user-1/delete",
  );
  assert.equal(
    adminEndpoint("delete", "projects", "project-1"),
    "/api/v1/admin/projects/project-1/delete",
  );
  assert.throws(() => adminEndpoint("unknown", "projects", "project-1"));
});

test("cancel can never submit an administrator action", () => {
  assert.equal(adminSubmissionState("cancel", "target", "target"), "cancel");
  assert.equal(adminSubmissionState("confirm", "wrong", "target"), "mismatch");
  assert.equal(adminSubmissionState("confirm", "target", "target"), "confirmed");
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
