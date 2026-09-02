# Temporary detached development pipeline

The main development workflow can run without a browser login while the agent
pipeline is being built. This is a temporary deployment mode, not a replacement
for the authenticated product boundary.

## Scope

When `auth.pipeline_mode = "detached"`, only the explicit pipeline from
Discovery through Build Preparation is detached:

```text
Discovery -> Content Architect -> Visual Design Director -> Build Preparation
```

The following remain authenticated or admin-gated: `/api/v1/me`, normal
owner-scoped product APIs, administrator APIs, fixture/dev-run APIs, legacy
run APIs, and Code Generator production/development surfaces. Docker and test
configuration remain attached by default; production rejects detached mode.

## Browser/session rules

- The detached bootstrap does not load Supabase, restore an identity, or send a
  bearer token.
- The workspace lists only allowlisted non-secret model-profile labels. A
  fixed no-context preflight must succeed before Discovery starts; the chosen
  profile is then locked and inherited by every remaining stage.
- The browser keeps only an opaque detached `session_id` in `sessionStorage`.
  It does not persist stage JSON, prompts, errors, agent output, or access
  tokens.
- Ordinary reloads perform a no-store GET of the remembered session and its
  durable stage state. The server/database is authoritative, so a stale error
  or old account's state cannot be restored from browser cache.
- The API and HTML shell send `Cache-Control: no-store, no-cache` and related
  revalidation headers. Detached requests explicitly use `cache: "no-store"`
  and remove any inherited `Authorization` header.
- In-flight requests are associated with a pipeline epoch and session ID.
  Responses from a previous session or epoch are ignored, preventing a slow
  old poll from repainting a restarted pipeline.

## Restart Pipeline

The Restart Pipeline control is shown throughout the detached workspace. It
requires confirmation and then:

1. Stops polling and aborts in-flight browser requests.
2. Creates a replacement UUID and calls
   `POST /api/v1/sessions/{old_session_id}/restart`.
3. The server locks and fences the old session, marks queued work failed with a
   restart reason, and commits that fence before cleanup.
4. Exact session-scoped database children, Build Preparation object metadata,
   temporary object-store keys, and configured local mirrors are cleaned up.
5. The old session is deleted and a new detached session is created with empty
   state, revision 0, and no inherited stage outputs.
6. The browser selects the replacement and starts again at Discovery.
7. The model selector is reset and unlocked; stale polling/progress state is
   discarded with the old pipeline epoch.

If the browser or network retries after the first request committed, the same
replacement ID is returned when the replacement is still the empty revision-0
session. A cleanup failure leaves the old session fenced and returns a safe
retryable error; it never reports a clean restart while artifacts may remain.

The next user submission, rather than the restart request itself, begins the
Discovery Agent run. No stage is automatically chained after approval.

## Reattaching authentication later

Set `auth.pipeline_mode = "attached"` in the deployment overlay and use the
authenticated bootstrap. The existing owner/admin dependencies then protect
the main pipeline routes again. The detached session classification and hard
restart cleanup should remain in the data model until all temporary detached
sessions have been retired safely.
