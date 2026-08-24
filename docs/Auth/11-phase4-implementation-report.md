# Authentication Phase 4 implementation report

Status: implemented locally; no production cloud resources were created.

This phase completes the administrator lifecycle on top of the Phase 1
identity boundary, Phase 2 ownership boundary, and Phase 3 entitlement and
worker-fencing boundary. The application remains database-authoritative:
Supabase Admin API calls are limited to provider identity suspend, restore, and
delete operations, while OryxenAI stores the local decision, operation state,
safe audit facts, and deletion tombstones.

## Delivered server behavior

- Added Alembic revision `0017_auth_admin_lifecycle` after the bounded
  `0016_auth_entitlements` revision. The migration adds lifecycle columns,
  deleted-project entitlement state, administrator audit and operation tables,
  identity and project tombstones, RLS enablement, and conditional privilege
  revokes. It has been rehearsed with upgrade, downgrade to `0016_auth_entitlements`,
  and upgrade back to head on the dedicated test database.
- Added bounded, server-only Supabase Admin API calls. Provider response bodies,
  secret keys, provider tokens, and raw identity data are not returned or
  written to logs.
- Added audited, idempotent administrator operations for suspend, restore,
  user deletion, project deletion, legacy-project deletion, identity readmission
  approval, entitlement reset, promotion, demotion, and operation resume.
- User deletion fences local identity and all owned projects first, cancels
  queued work, waits for running work to finish, removes exact preview/artifact/
  local run data, records tombstones, deletes the provider identity, and is
  resumable after provider or storage failure. Deleted identities are not
  automatically readmitted; readmission requires an explicit administrator
  operation and re-enters through a new provider login.
- Promotion removes normal-user entitlement limits without deleting the active
  project. Demotion requires capacity, preserves at most one live project and
  its verified success binding, and rejects unsafe multi-project cleanup.
- Worker authorization rejects deletion-pending and deleted portfolio work.
  Existing Code Generator retry/regenerate commands are available through the
  same admin operation/audit boundary.

## Delivered admin surface

The authenticated `/admin` shell now loads safe, masked, cursor-paginated
summary, user, project, legacy-project, deleted-identity, pending-operation,
and audit views. It
supports explicit typed confirmation, optional reason text, stable
`Idempotency-Key` reuse across retries, one-time authorized fetch refresh, and
logout. It never renders full email addresses, provider subjects, JWTs, secret
keys, allowlists, or provider response bodies.

Admin API routes are under `/api/v1/admin`; every route is protected by the
active, onboarded administrator dependency. Mutations require a strict body,
target confirmation, and a bounded idempotency key. Read pages use opaque
bounded cursors and safe projections.

## Verification evidence

Focused proof completed during implementation includes:

- dedicated PostgreSQL migration upgrade/downgrade/upgrade rehearsal;
- provider, timeout, rate-limit, redaction, masking, and cursor unit tests;
- admin inventory authorization and masked-projection API tests;
- failed provider deletion followed by successful same-key resume, with local
  deleted state and an identity tombstone asserted;
- existing auth, ownership, entitlement, worker-fence, and route-inventory
  regression tests;
- Node built-in tests for the auth controller and admin endpoint/no-fetch
  behavior;
- owned-scope Ruff, Ruff format, and mypy checks, browser syntax checks, and the
  self-hosted browser bundle build.

The full repository test suite is green. The repository-wide Ruff check and
format check still report only the pre-existing, explicitly preserved
untracked `test_openai_check.py`; repository-wide mypy still reports only
pre-existing typing errors in the untouched Build Preparation/Code Generator
files `src/oryxenai/agents/build_preparation/visual_input.py`,
`src/oryxenai/agents/shared/resource_context.py`,
`src/oryxenai/agents/build_preparation/providers.py`,
`src/oryxenai/agents/build_preparation/materializer.py`,
`src/oryxenai/agents/build_preparation/quality.py`, and
`src/oryxenai/agents/build_preparation/agent.py`. The Phase 4-owned source
scope is clean under those checks.

## Final readiness audit

A post-implementation audit corrected release-blocking edge cases without
creating production resources:

- Modern `sb_secret_...` keys are sent to Supabase as server-side `apikey`
  headers, never misrepresented as bearer JWTs. Legacy service-role JWTs remain
  supported during migration. A response-body-free server probe returned 200.
- The protected browser fetch boundary consumes its bootstrap access token
  once, reads current Supabase session state on later calls, coalesces refresh,
  clears local provider state after terminal 401s, and refuses to attach a
  bearer token outside reviewed local `/api/v1/...` paths.
- Browsers opened on an allowed non-primary origin move to the configured
  primary origin before PKCE starts, preventing verifier loss when OAuth
  returns to the canonical callback origin.
- The admin shell exposes pending/retryable operations, safe resume, append-only
  pagination, and guards against cancel-as-confirm, unsafe self-actions, and
  Code Generator commands on legacy projects.
- Provider deletion no longer waits while holding application row locks;
  deletion re-locks and validates local state before finalization. Artifact
  storage is created lazily only when cleanup finds a typed reference, and
  demotion rejects more than one session-mode generation variant.
- Readiness now verifies the minimum migrated schema instead of reporting ready
  after only `SELECT 1`.

The previously reported application database inconsistency contained no
application tables or user data. The stale version row was safely stamped to
base and the complete Alembic chain was applied to
`0017_auth_admin_lifecycle`. The Docker migration service then completed, and
the API, PostgreSQL, and worker were healthy with a recent worker heartbeat.
No database was dropped or reset.

## Explicit boundary

Authentication and local authorization implementation are complete through
Phase 4, including audited administrator lifecycle and deterministic
end-to-end verification. Production cloud deployment remains a separate
owner-authorized task; any real Google browser step not personally completed by
the owner is reported as an acceptance gate, never claimed as automated
evidence.
