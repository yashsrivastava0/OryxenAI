# Active Agent Deep Dive

This document is a current guide to the two active portfolio agents. It summarizes the boundaries that keep each stage understandable and independently reviewable.

## Discovery

Discovery turns a user's intake into an approved brief through an explicit question and review loop. Its state machine covers intake, questions, brief drafting, revision, approval, and visible recovery from errors. Its model output is envelope-validated; the brief remains user-readable free text.

Discovery owns its persisted input and output under the session state. Approval stamps the brief content hash and session revision. A later edit or reapproval is detected as a changed source by Content Architect.

The main implementation surfaces are src/oryxenai/agents/discovery/, src/oryxenai/api/routes/discovery.py, and frontend/src/stages/discovery/DiscoveryStage.tsx.

## Content Architect

Content Architect consumes only the compact approved Discovery snapshot. It does not receive raw resume or document text. One durable build job may call plan_content, write_pages, and integrate_content in sequence, with later calls used only when the earlier output requires them.

Its contract separates structured identifiers and publication decisions from flexible strategy and copy. Validators enforce stable route and claim identifiers, required public scope, and internal review boundaries while leaving visitor-facing prose free-form. Approval verifies the public route scope and stores a content hash.

The main implementation surfaces are src/oryxenai/agents/content_architect/, src/oryxenai/api/routes/content_architect.py, and frontend/src/stages/content/ContentStage.tsx.

## Product interaction

frontend/src/app/AppShell.tsx restores both stage states, gates Content Architect on Discovery approval, and starts each job only after an explicit action. frontend/src/app/url-state.ts accepts the two supported stage identifiers. The stage adapters fail closed on unknown statuses and expose only safe error fields.

The journey rail, progress and attention panels, content review surfaces, output inspector, polling coordinator, and cross-tab invalidation are shared UI infrastructure. They do not create additional agent stages.

## Verification map

- Discovery domain and workflow: tests/unit/agents/discovery/ and tests/api/test_discovery_flow.py.
- Content Architect domain and workflow: tests/unit/agents/content_architect/ and tests/api/test_content_architect_flow.py.
- Durable job behavior: tests/integration/ and tests/worker/.
- Authenticated product journey: tests/frontend/ and tests/browser/.

The source and tests are authoritative if any older narrative disagrees with the current implementation.