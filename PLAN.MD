# Code Generator reliability: pre-live fixes, offline verification, bounded 5-run campaign

## 1. Objective and confirmed starting state

Make the existing Code Generator reliably produce a desktop web portfolio from
an approved Build Preparation brief, with no build/runtime errors and a real
frontend preview. Optional imagery may be absent, but a rendered image must
never be broken. This campaign keeps the durable API → PostgreSQL job → worker
→ preview-gateway path and does not replace the pipeline.

The previous final reliability campaign on 2026-09-10 consumed all five slots
and accepted 0/2 portfolios. Each terminal result was a distinct,
root-causable defect rather than a repair that was still converging when its
budget ended. Pack A slot 5 (20bdd7df-4604-48e0-ba36-3022eab10f0a, source
checkpoint 93c27537190a996a6b8ddaa67d1468561430b49da6654c26a55293cbeb85a4e4)
reached source generation, clean build, and integration review; its only
blocking result was a false negative for a statically provable conditional JSX
motion marker. Commit c3fabdc fixed that validator gap offline, but it was
not exercised live before the previous cap ended.

The earlier commit 39076d0 also refreshed stale Pixabay pins and made failed
exports truthful about partial dist/ state. Those changes are present but
still need live confirmation. Missing dist/ on runs that never reach
SOURCE_READY is expected; export_failed_run() already performs one
best-effort build attempt for failed runs. The next reliability gain is to get
more runs through source readiness, not to force an export.

Image handling is already fail-safe: optional/preferred images can fall back
or be absent, while a genuinely broken rendered <img> remains blocking.
Further Pexels/Unsplash URL-refresh or attribution work is deferred because no
live failure evidence points there.

## 2. Step 1 — pre-live fix and decision boundary

The Pydantic defaults in src/oryxenai/core/settings.py now match the
effective canonical values in config/app.toml:

    max_repair_rounds_per_unit = 2
    max_repair_rounds_total = 4
    max_integration_polish_rounds = 3  # bounded by ge=1, le=6

The comment beside those defaults explains the current rationale: the tighter
values already governed the completed live campaign, and its terminal failures
were distinct defects, not genuine repair-round starvation. config/app.toml
is unchanged and remains the source of effective application configuration.

The dead repair_depth field remains at its three write sites in
jobs/handlers/code_generator_verification.py. It is not read; the real
bound is RepairBudget in core/repair_policy.py. Removing it immediately
before live spending would add risk without behavioral value, so this is an
explicit non-decision recorded in D-089.

No force-dist mechanism is added, and image_retrieval.py is not changed.

## 3. Step 2 — offline verification gate

Run the repository checks before reserving a paid slot:

    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src
    uv run pytest

Reconfirm the fixes landed since the previous live campaign by running each
of these suites:

    tests/unit/agents/code_generator/test_source_validation.py
    tests/unit/agents/code_generator/test_typescript_ast_audit.py
    tests/unit/agents/code_generator/test_final_repair.py
    tests/unit/agents/code_generator/test_v4_contracts.py
    tests/unit/agents/code_generator/test_generation_contracts.py
    tests/unit/agents/code_generator/test_portfolio_export.py
    tests/unit/agents/build_preparation/test_image_retrieval.py

Also run uv run pytest -k code_generator -q, the verification-worker test,
and the settings-file mypy/Ruff checks. Record pass/fail counts and separate
pre-existing fixture, database, Windows-permission, and unrelated-worktree
failures from regressions caused by this task. Do not silently claim a green
repository-wide baseline when those exceptions remain.

Replay the exact failed source trees without model calls or npm install.
Copy each saved repo/ to a disposable temporary directory, leave the saved
tree untouched, and run npm run source:audit followed by npm run typecheck:

| Historical failure | Saved source tree | Required evidence |
| --- | --- | --- |
| Pack A, slot 5 | .workspace/code-generator-generation/20bdd7df-4604-48e0-ba36-3022eab10f0a/repo/ | Zero audit/typecheck diagnostics for the conditional JSX motion marker fixed by c3fabdc. |
| Pack B, slot 3 | .workspace/code-generator-generation/7b74c97b-f95e-4b77-986c-a6aed0f99b78/repo/ | Route-contract diagnostics surface before and independently of typecheck. |
| Pack B, slot 4 | .workspace/code-generator-generation/fe4a0224-8f5f-4c3e-86a2-a1aafef8d621/repo/ | No false-positive diagnostics for literal object/tuple content-key maps. |

Repair-context plumbing and interaction-ownership attribution are behavioral
fixes; their unit-test coverage is the offline confirmation for those cases.

## 4. Step 3 — bounded five-run campaign

Before every slot, check the real current balance of the configured provider
account directly. Do not use a stale remembered balance. If the balance is
not available or cannot safely cover one more full run, stop and report it.
Billing or authentication failure does not consume a campaign slot.

Run one slot at a time through the normal API, durable job, worker, and
preview-gateway path. Start the configured API, worker, and preview gateway;
run provider/toolchain preflight; reserve the slot; then drive the run through
the normal product surface. Do not invoke a handler directly or substitute a
fixture for a live model response.

The pack order is deliberately changed from the old B-first order because A
is now the strongest direct confirmation target: its previous furthest run
was blocked by the validator fixed in c3fabdc and that exact tree now passes
offline. The campaign cycle is:

1. Pack A — 5f144f04-2789-48c6-9b1c-6bd11c87abdb.
2. Pack B — ba4b986e-7841-4cfb-94a0-d56fbe1b7956.
3. Pack C — c0860464-a786-43d8-9c30-d12d7516c4b8.
4. Pack A again if another slot is needed.

If a run fails, inspect its database row, the exact background-job error, the
accepted checkpoint tree, and repair receipts before writing a fix. A retry
uses the same pack after the root cause is fixed and its offline regression is
green. A successful run advances to the next different pack. Stop at the
first of two cross-pack ready portfolios, five consumed live runs, or an
insufficient balance. There is no sixth run and no automatic follow-on
campaign.

### Ready acceptance checklist

- npm run build exits 0 with zero source-audit/typecheck diagnostics.
- Desktop (1440x900) and laptop (1280x800) journeys have zero console errors,
  page exceptions, or failed network requests. Mobile is not a gate under
  D-088.
- No broken <img> exists; every rendered image uses a host-admitted path.
  Zero visible images is valid.
- Navigation and required interactions work in the browser.
- Integration/quality review has no unresolved blocking finding.
- A promoted preview is reachable through the frontend, loads in an actual
  browser, and its iframe handshake connects and reconnects after refresh and
  route changes.
- dist/index.html exists as a consequence of the verified build; it is never
  forced separately.

Append each run's outcome to docs/code-generator-live-campaign.md immediately
after it completes. Add one dated root-cause entry to code generator
issues.md for each new fix, and a matching CHANGES.md entry before the
task-scoped commit.

## 5. Azure compatibility, privacy, and handoff

Prepare for the existing Linux/Docker architecture on an Azure VM; deployment
itself is not part of this fix campaign.

- Use the existing application image, separate API/worker/gateway services,
  and configured private preview storage.
- Run model-free install, TypeScript, build, Chromium, artifact-storage, and
  gateway checks as the container's non-root user.
- The current Docker overlay disables Code Generator verification and uses
  localhost preview values. Document the required deployment configuration:
  enable verification, provide a browser-reachable HTTPS preview URL, retain
  the internal gateway health URL, and configure the exact application embed
  origin.
- Do not claim Azure readiness from Windows tests alone. If Linux execution is
  unavailable, record that specific verification gap.
- Preserve CSP, owner authorization, worker reauthorization, immutable
  artifacts, and atomic preview promotion.

Keep prompts, briefs, source evidence, and screenshots local/private. Do not
publish a site, send messages, upload evidence externally, push commits, or
expose credentials.

Preserve unrelated dirty worktree changes. Never use git add . or git add -A;
stage only this task's files or exact hunks. Run git diff --cached --check,
review the staged patch, and make one local task-scoped commit per completed
verified unit. Do not amend, rebase, or push.

The final handoff identifies the fixes, offline results, campaign consumption,
browser-loaded preview evidence, remaining limitations, and local commit
hashes. Stop as soon as the acceptance condition or another stated stop
condition is reached.
