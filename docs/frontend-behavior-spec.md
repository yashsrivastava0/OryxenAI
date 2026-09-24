# Frontend behavior specification — Discovery and Content Architect

This document describes the current authenticated Preact product workspace.
The active user journey ends after Content Architect approval.

## 1. Product boundary

The workspace presents Discovery followed by Content Architect. Discovery
collects the user's intent, asks clarifying questions when needed, and
produces a reviewable brief. The user explicitly approves that brief before
Content Architect can start. Content Architect produces a grounded content
plan for review and approval.

Approval does not start another operation automatically. Content Architect
approval is the terminal step of the current product journey.

## 2. Session and state lifecycle

Stage state is persisted server-side and loaded through owner-scoped API
routes. The browser polls stage and durable-job status; it does not treat
browser state as an authorization boundary.

Discovery progresses through question queuing/running, answer collection,
brief creation/review, and approval. Failures enter needs_attention and
expose a safe recovery action. Brief revisions are allowed while under review.

Content Architect progresses through build_running, content_review, and
approval, with needs_attention for terminal failures. Revisions rerun its
bounded workflow while the output remains under review. Approved state is
terminal for both stages.

## 3. Discovery interaction

Discovery accepts user-provided text, an optional plain-text document, and a
goal. It can ask focused questions, one at a time, before drafting the brief.
The interface shows questions with the available answer options and lets the
user provide a written answer or skip when allowed.

The Discovery result includes a full editable Markdown brief, a user-facing
summary, and a structured profile. The user can review, edit or request a
revision, then explicitly approve the current brief.

## 4. Content Architect review

Content Architect starts only from the approved Discovery snapshot. The
server sends a compact approved projection; raw document text and the full
Discovery prose are not included in its input.

The workspace presents the route/content plan, publishable copy, and review
notes needed for user approval. Revisions are allowed until approval. Internal
review annotations, worker metadata, prompt details, and provider credentials
are not part of the public content projection.

## 5. Errors and progress

The UI reads durable stage state and job progress from the API. Retryable
provider or invalid-output failures follow the configured worker retry policy.
When retries end, a safe error is shown with a recovery action. The client
must not invent success from a request timeout or a stale poll response.

## 6. Provider selection and privacy

Model profile choices come from safe, non-secret server projections. Secrets,
provider credentials, raw stack traces, and server-only endpoints stay on the
server. Source documents and answers are treated as untrusted input.

Discovery and Content Architect use the provider-neutral ModelClient
contract. Configuration in config/models.toml controls model routing.

## 7. Current limitations

- Document intake is plain text; unsupported document formats must produce a
  visible error instead of silently dropping their content.
- Progress uses polling and does not expose token-level model streaming.
- The current product stops after approved content and does not render a
  finished portfolio site.
- Migrations run before API and worker startup; API and worker remain separate
  processes.

## 8. Implementation sources

- frontend/src/app/ and frontend/src/stages/ define the authenticated UI.
- src/oryxenai/agents/discovery/ defines Discovery state and prompts.
- src/oryxenai/agents/content_architect/ defines content review contracts.
- src/oryxenai/api/projections.py filters session and run output.
