# Frontend behavior specification — Explorer, Content Architect and Studio

This document describes the current authenticated Preact product workspace.
The active user journey ends in the Studio, where the approved content
becomes a live, editable portfolio page.

## 1. Product boundary

The workspace presents Explorer followed by Content Architect. Explorer
collects the user's intent, asks clarifying questions when needed, and
produces a reviewable brief. The user explicitly approves that brief before
Content Architect can start. Content Architect produces a grounded content
plan for review and approval.

Approval does not start another operation by itself. The Content Architect
review's primary action is one explicit click, "Approve & generate my
portfolio": the browser approves the plan, then calls the Studio start
endpoint, then opens the Studio. If the approval is rerouted into a safety
revision, no build starts. No API endpoint chains stages.

The Studio (third journey stage) shows, from the server's state: locked until
the plan is approved; an explicit Generate action if no build exists (also the
recovery path when the automatic start after approval failed); full-page
progress with plain stage names and Stop for the first build; an exact failure
panel (what happened, where, why, what to do, reference, copy diagnostics) with
a retry; and the workspace. The workspace has the change chat on the left
(timeline, suggestions, versions with restore, composer) and the live preview
on the right (desktop/tablet/mobile width, fit or 100%, reload, open in a new
tab, two frames swapped on load so the current page stays until the next one
has loaded). Narrow screens show one pane at a time behind Chat and Preview
tabs. The preview iframe is sandboxed without `allow-same-origin` and
`allow-scripts`. While a build runs the browser polls every two seconds; the
composer is disabled and a Stop control is shown.

## 2. Session and state lifecycle

Stage state is persisted server-side and loaded through owner-scoped API
routes. The browser polls stage and durable-job status; it does not treat
browser state as an authorization boundary.

The sticky workspace header keeps Reset pipeline in the same position across
Explorer, Content Architect, and Studio. After explicit confirmation, the
owner-scoped reset fences active work and clears intake, answers, plans, page
versions, and chat, then returns to empty Explorer in the same portfolio
session. The browser clears its local intake draft and reloads server state.

Explorer progresses through question queuing/running, answer collection,
brief creation/review, and approval. After any contextual questions, a fixed
palette question is always shown; even when the model has no clarification to
ask, the brief waits for that selection.
Failures enter needs_attention and expose a safe recovery action. Brief
revisions are allowed while under review, and a failed revision retry retains
the user's revision request.

Content Architect progresses through build_running, content_review, and
approval, with needs_attention for terminal failures. Revisions rerun its
bounded workflow while the output remains under review. Approved state is
terminal for both stages.

## 3. Explorer interaction

Explorer accepts user-provided text and one optional PDF, Markdown, or UTF-8
plain text attachment, plus a goal. The attachment control is in the intake
composer and a file alone can start Explorer. The frontend displays an
editable transcript before submission. Selectable PDF text is kept as the
source of truth; local OCR reads image regions and scanned pages while Docling
returns headings, lists, reading order, and page boundaries as Markdown. The
original file bytes are not retained. Explorer receives the reviewed text as
an attached source document and can ask focused questions before drafting.
Every new contextual question shows three relevant options and one custom
answer box; older saved text or boolean questions remain readable. Users can
select a choice, write their own answer, add detail, or skip when allowed.
The final visual question shows three miniature portfolio looks with swatches,
style descriptions, and an optional reference note. A
palette selection is required to continue; the server maps it to a pinned
theme, while the note does not affect that mapping.

The Explorer result includes a Markdown brief, a user-facing summary, and a
structured dossier and profile. The user can review or request a revision,
then explicitly approve the current brief. The evidence inspector presents
facts, roles, projects, open items, and explicit restrictions even when the
dossier has no span-level coverage rows.

## 4. Content Architect review

Content Architect starts only from the approved Explorer snapshot. The
server sends a compact approved projection; raw document text and the full
Explorer prose are not included in its input.

The workspace presents the route/content plan, publishable copy, and review
notes needed for user approval. Revisions are allowed until approval. Internal
review annotations, worker metadata, prompt details, and provider credentials
are not part of the public content projection.

## 5. Errors and progress

The UI reads durable stage state and job progress from the API. Explorer polls
while work is active, shows elapsed time and whether a job is queued or
running, and keeps an earlier brief visible during revision. Retryable
provider or invalid-output failures follow the configured worker retry policy.
When retries end, a safe error is shown with a recovery action. The client
must not invent success from a request timeout or a stale poll response.

## 6. Provider selection and privacy

Model profile choices come from safe, non-secret server projections. Secrets,
provider credentials, raw stack traces, and server-only endpoints stay on the
server. Source documents and answers are treated as untrusted input.

Explorer and Content Architect use the provider-neutral ModelClient
contract. Configuration in config/models.toml controls model routing.

## 7. Current limitations

- DOCX, image attachments, and multi-file intake are not yet supported.
  OCR can make recognition errors on low-quality scans; the transcript is
  shown for review and editing before Explorer starts.
- Progress uses polling and does not expose token-level model streaming.
- The generated page is previewed for its owner only; there is no publish,
  export or public hosting step.
- Chat changes cover wording and content. The palette chooses one of three
  pre-built themes during Explorer; later chat does not change colors,
  layout, or scripts.
- Migrations run before API and worker startup; API and worker remain separate
  processes.

## 8. Implementation sources

- frontend/src/app/ and frontend/src/stages/ define the authenticated UI.
- src/oryxenai/agents/discovery/ defines Explorer state and prompts.
- src/oryxenai/agents/content_architect/ defines content review contracts.
- src/oryxenai/agents/code_generator/ defines the Studio pipeline and API.
- frontend/src/stages/studio/ and frontend/src/components/studio/ define the Studio UI.
- src/oryxenai/api/projections.py filters session and run output.
