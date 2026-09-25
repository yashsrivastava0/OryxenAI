# Current Frontend Implementation Audit

> **Purpose:** Describe the authenticated Preact/TypeScript product frontend as it exists now. This is a current implementation guide; verify details against the files listed below when the code changes.

## Active journey

The product journey has two explicitly started stages: Discovery, followed by Content Architect. Discovery gathers the user's intent and produces an approved brief. Content Architect consumes that approved brief and produces site routes, positioning, and page content. Approval of Content Architect is the terminal active workflow. There is no later stage in the product UI or API client.

## Application shell

frontend/src/app/AppShell.tsx owns session restoration, API coordination, stage selection, mutations, error recovery, and rendering. On restoration it loads the session, Discovery state, and Content Architect state. Discovery approval unlocks Content Architect; stale or invalid stage URLs are corrected to an available stage.

frontend/src/app/store.ts holds the shell state and reducer. frontend/src/app/url-state.ts accepts only the discover and content stage identifiers and the supported view identifiers. frontend/src/main.tsx boots, stops, and restarts the product shell.

## Stage controllers

| Stage | Controller | Main user actions |
| --- | --- | --- |
| Discovery | frontend/src/stages/discovery/DiscoveryStage.tsx | Start with intake, answer or skip questions, request a brief, retry, revise, approve |
| Content Architect | frontend/src/stages/content/ContentStage.tsx | Start after brief approval, review routes and copy, revise, retry, approve |

Both stages use explicit mutations. Completing or approving Discovery does not silently start Content Architect; the user must explicitly start the next stage. Content Architect approval ends the active journey.

## API and state adapters

frontend/src/data/api-client.ts defines the browser boundary for session, Discovery, Content Architect, and diagnostics requests. It sends idempotency keys for supported mutations and returns typed envelopes where the server contract permits them.

frontend/src/data/adapters/discovery.ts and frontend/src/data/adapters/content.ts convert untrusted server payloads into view models. Shared status and error handling lives in frontend/src/data/adapters/types.ts; job selection lives in frontend/src/data/adapters/job.ts. Unknown statuses remain unsupported instead of being treated as successful.

## Shared interaction and recovery

Reusable components in frontend/src/components/ provide the journey rail, conversation surface, progress and attention states, content review, output inspection, safe Markdown rendering, and accessible announcements. PollCoordinator refreshes durable work state. A BroadcastChannel invalidates stale state across tabs, and online events trigger recovery reads. Session-scoped idempotency keys protect retried mutations.

## Diagnostics and output

The client trace notice and output inspector expose safe, user-visible diagnostics. Diagnostic payloads are built by frontend/src/data/client-diagnostics.ts; provider response bodies and credentials are not part of the public error view. frontend/src/data/final-agent-output.ts projects the stored Discovery and Content Architect outputs without reconstructing them from presentation cards.

## Tests

Frontend tests are maintained under frontend/src/ and tests/frontend/; browser journey acceptance tests are under tests/browser/. The canonical repository commands in AGENTS.md define lint, type-check, and test execution. Do not infer the current stage count or API surface from historical change records.