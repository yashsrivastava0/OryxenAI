# OryxenAI — Decisions & Open Issues

Architecture Decision Record (ADR) log of architectural choices, trade-offs, and invariants. Read before making design changes.

**Policy:**
- Log only real architectural decisions with concrete trade-offs (not routine code changes).
- Maintain reverse-chronological order (newest first under `## Active Decisions`). Entry IDs (`D-001`, `D-002`, ...) are permanent and never reused.
- Keep entries high-density, concise, and machine-readable for AI agents.
- When superseded, move the entry to `## Compacted & Superseded History` with a single-line summary referencing the superseding decision.

**Entry Template:**
```markdown
## D-0XX — <short decision title>

- **Date & Time:** YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>)
- **Status:** open | decided-not-yet-implemented | decided-implemented | superseded-by-D-0YY
- **Context:** Constraint or problem forcing a choice.
- **Decision:** What was chosen, stated concretely.
- **Rejected alternatives:** What else was considered and specifically why rejected.
- **Consequence:** Forward implications, trade-offs, and invariants.
```

---

## Active Decisions

## D-111 - Resolve npm portably by platform, never trust a hardcoded wrapper-name override

- **Date & Time:** 2026-09-22 14:20 +05:30 - Claude Sonnet 5 (Anthropic)
- **Status:** decided-implemented
- **Context:** PR #1's required `quality` check failed on Linux CI with `COMMAND_START_FAILED: ... No such file or directory: 'npm.cmd'`. Root cause: `config/app.toml` and `config/app.test.toml` hardcoded `npm_executable = "npm.cmd"` — a Windows-only wrapper filename — while `app.native.toml`/`app.production.toml`/`app.docker.codegen-run.toml` already correctly used the portable `"npm"`. `config/app.docker.toml` has no override for this key, so it deep-merge-inherited the bad value from `app.toml`, meaning the real Linux/Docker Azure production path had the identical bug, not just CI: the live Code Generator's build-verification step (`npm ci`/`npm run build`) would fail identically once real generation runs happen on the VM. Beyond the bad config value, `resolve_npm_executable()` (`process_runner.py`) had no platform awareness at all: when a configured override failed to resolve via `shutil.which`, it returned the unresolved literal verbatim rather than degrading to the portable bare name — so any future bad or Windows-specific value in a shared config profile would reproduce this exact failure class again.
- **Decision:** Changed `config/app.toml`/`config/app.test.toml` to `npm_executable = "npm"`. Hardened `resolve_npm_executable()` so an unresolved configured value is trusted verbatim only when `sys.platform == "win32"` or it is an existing absolute path; otherwise it retries `shutil.which("npm")` before giving up. `shutil.which` already resolves bare `"npm"` to `npm.cmd`'s full path on Windows via `PATHEXT`, so this changes no local Windows dev behavior.
- **Rejected alternatives:** Fixing only the config value — would remove today's instance but leave the resolver still willing to propagate a future bad literal unconditionally on any OS, reproducing this same bug class. Fixing only the resolver and leaving `npm.cmd` in config — would leave the wrong value sitting in the base profile as a trap for any code path that reads it directly instead of through the resolver.
- **Consequence:** All profiles now agree on the portable `"npm"` value, and the shared resolver fails safe (falls back to the real platform-appropriate binary) instead of propagating an unresolvable literal. Both CI failures this caused (`test_verification_builds_and_promotes_a_clean_candidate`, `test_supported_dependency_never_synthesizes_a_package_install_and_unsupported_uses_fallback`) are fixed without any test-file changes, since the underlying commands now actually execute. See `CHANGES.md` `1be4b13`.

## D-110 - Fully automatic CD via a self-hosted GitHub Actions runner on the Azure VM

- **Date & Time:** 2026-09-22 11:30 +05:30 - Claude Sonnet 5 (Anthropic)
- **Status:** decided-implemented
- **Context:** D-107 kept Azure deployment entirely manual (a human runs `azure-deploy.sh deploy` over SSH). The owner asked for that to become automatic after every push. The obvious mechanism — a GitHub Actions job SSHing into the VM — runs into a real constraint of this specific VM: its NSG allows inbound SSH from exactly one hand-picked IP at a time (see `docs/azure-issue.md`'s multi-session SSH-connectivity saga: Jio hotspot, Cloudflare WARP, and office Wi-Fi each needed a manual NSG edit). GitHub-hosted runners connect from large, rotating Microsoft/GitHub IP ranges, so an SSH-based pipeline would need the NSG opened to the broader internet (or a large, shifting range) to work reliably — reintroducing the exposure the single-IP rule exists to prevent, and reintroducing the exact IP-mismatch failure class already spent on manual SSH. An initial draft of this decision also added a `production` GitHub Environment approval-click gate (reasoning: an AI agent, not only the owner, would be producing many of the deployed changes); the owner then explicitly asked for fully automatic deploy instead, "temporarily," with the explicit understanding it's easy to re-add later.
- **Decision:** Install a self-hosted GitHub Actions runner directly on the VM (as `oryxenaiadmin`, systemd-managed) so it polls GitHub over outbound HTTPS — no inbound port, no SSH key in GitHub, no NSG change, ever, and no GitHub Actions secrets of any kind needed for the deploy job. Add a `deploy` job to the existing `ci.yml` (`needs: quality`, restricted to `push`/`workflow_dispatch` on `deployment`, `runs-on: [self-hosted, azure-oryxenai]`) that runs `./scripts/azure-deploy.sh deploy ${{ github.sha }}` then `verify` directly in the VM's persistent repo directory — no `actions/checkout`, since the script already does its own `git fetch`/`checkout --detach`. **No approval gate**: the job runs immediately once `quality` passes on a push to `deployment`. On failure, dump `status`/`logs` into the Action's own output; no auto-rollback (same reasoning D-107 originally gave for rejecting it — a human decides the next step).
- **Rejected alternatives:** SSH-from-GitHub-hosted-runner with NSG opened to GitHub's published Actions IP ranges — rejected as both more complex to maintain (those ranges rotate and are still broad) and not actually simpler or safer than a self-hosted runner. A `production` Environment approval-click gate was built and then explicitly removed per the owner's follow-up instruction — recorded here, not silently dropped, so a future session understands why the workflow has no `environment:` line despite this history; re-adding it later is a two-line change (see the comment left in `ci.yml` above the `deploy` job). Auto-rollback on failure — rejected for the same reason D-107 rejected it originally.
- **Consequence:** Supersedes D-107's "manual SSH only" stance; D-107 is moved to Compacted & Superseded History. The `Allow-SSH-MyIP` NSG rule is untouched by this change and remains only for interactive operator debugging. The single remaining trust boundary is now "who can push to `deployment`" — anyone (human or agent) who pushes a commit that passes `quality` deploys it to production immediately, with no human review step. Day-to-day flow becomes: commit -> push to `deployment` -> CI -> automatic `deploy`+`verify` on the VM's own runner, with failure diagnostics surfaced in the Actions tab.

## D-109 - `backend` Compose network must not be Docker-`internal`

- **Date & Time:** 2026-09-22 10:45 +05:30 - Claude Sonnet 5 (Anthropic)
- **Status:** decided-implemented
- **Context:** The first real rehearsal deploy against the Azure VM built all four images successfully but then failed with `EAI_AGAIN` (DNS resolution failure) during npm-cache warm-up. Investigation found `compose.production.yaml`'s `backend` network declared `internal: true`, with `app`, `worker`, `migrate`, and `preview-gateway` (via the shared `&application` anchor) attached only to it. Docker's `internal: true` blocks all outbound routing for a network, not just inbound exposure — so as configured, `worker` and `app` would have had zero outbound internet access in production at all (no Supabase, no model provider calls, no npm registry), not just a broken warm-up step. The comment justifying `internal: true` was actually about preventing *inbound* exposure, a separate property already guaranteed by the fact that only `caddy` publishes a host `ports:` mapping.
- **Decision:** Removed `internal: true` from `backend`. It stays a private, non-published bridge network (no service other than `caddy` has a `ports:` entry, so nothing is reachable from outside the Docker host), but now has normal outbound NAT/egress. See `docs/azure-issue.md` for the full failure log and local verification evidence.
- **Rejected alternatives:** Keeping `internal: true` and adding an explicit egress path (a NAT/forward-proxy sidecar container) — rejected as unnecessary complexity solving a problem that doesn't exist once inbound isolation is understood to come from the absence of published ports, not from the network's `internal` flag.
- **Consequence:** `app`/`worker`/`migrate`/`preview-gateway` can now reach Supabase, model provider APIs, and the npm registry from production. Any future change to this compose file must not reintroduce `internal: true` on `backend` without also giving those services another route to the internet.

## D-108 - Record the registered production domain

- **Date & Time:** 2026-09-21 17:39 +05:30 - Claude Sonnet 5 (Anthropic)
- **Status:** decided-implemented
- **Context:** D-098 deployed the server against the placeholder domain `deploy.me` pending real domain registration. The real domain `oryxenai.me` has since been registered, and Namecheap DNS, Supabase Site/redirect URLs, and the Google OAuth client have all been configured against `app.oryxenai.me` / `preview.oryxenai.me`. No decision entry recorded this switch; only `CHANGES.md`/`docs/project-status.md` carried the fact.
- **Decision:** `app.oryxenai.me` and `preview.oryxenai.me` are the production hostnames, superseding every `deploy.me` reference in D-098 and any doc still naming that placeholder.
- **Rejected alternatives:** None — this records an already-made external registration decision so DECISIONS.md stops being the one place that still names the old placeholder.
- **Consequence:** `config/app.production.toml`, `Caddyfile`, `.env`/`.env.example`, and all deployment docs use the real domain. D-098 is superseded by this entry for the domain identity question; its infrastructure-before-DNS sequencing point still stands.

## D-106 - Use VM-local persistent storage for the first Azure release

- **Date & Time:** 2026-09-20 22:37 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-not-yet-implemented
- **Context:** The first release is intentionally a single Azure VM and a small demo. Adding R2 would introduce a second storage service, credentials, lifecycle policy, and another live acceptance boundary while the VM already provides persistent disk and Docker-backed volumes.
- **Decision:** Store PostgreSQL data, generated artifacts, preview objects, required worker workspaces/checkpoints/caches, and Caddy state on VM-local persistent storage. The worker and shared preview gateway use the same durable preview root where required. Supabase remains the authentication service; R2 endpoints, buckets, and keys are not part of the first-release production configuration.
- **Rejected alternatives:** R2 was rejected for the first release because it adds external credentials and readback dependencies; Azure Blob was rejected because it would add another provider-specific adapter and deployment path. Per-portfolio containers were rejected because the shared preview gateway already provides the required boundary.
- **Consequence:** The Docker/config follow-up must select the available local-filesystem providers, remove R2-only setup and preflight requirements, enforce non-root ownership, and add disk monitoring plus filesystem backup/restore and restart-readback checks. Existing R2-compatible code may remain for compatibility, but it is not the selected production path. Reintroducing object storage requires a new decision.

## D-105 - Keep quality-review defects previewable without certifying them

- **Date & Time:** 2026-09-20 14:45 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** A live Code Generator attempt produced a complete source checkpoint, but the model's whole-site quality receipt contained an empty evidence marker. Treating that optional review response as a generation blocker left the frontend with only "Generation needs attention" even though the source could still be built and inspected. A later recovery attempt also exposed a transient Windows Vite child-process `spawn EPERM` immediately after the clean install.
- **Decision:** Treat only the whole-site quality receipt as degradable: malformed, unavailable, stale, or rejected quality output becomes a durable advisory, while source-contract, build, runtime, navigation, accessibility, and asset gates remain blocking. When those required gates pass, store an owner-scoped `candidate_preview` marked `unverified`; never promote it to `active_preview` or `ready` until a valid quality receipt is present. Add one bounded, model-free build retry for the classified Windows Vite spawn race.
- **Rejected alternatives:** Making all verification findings advisory would certify broken portfolios; hiding the candidate until a new model call would waste the user's live-call budget and prevent inspection; automatically retrying the full pipeline would create duplicate work and race the durable job; retrying the Vite build indefinitely would mask a persistent toolchain failure.
- **Consequence:** The Preact Generate & Preview surface can show a truthful unverified portfolio plus the existing retry action when quality review is the only defect, while the entitlement and verified active-preview boundaries remain fail-closed. The worker can recover one transient Windows Vite launch denial without spending model or repair budget.

## D-104 — Reuse the product Generate & Preview surface for standalone run acceptance

- **Date & Time:** 2026-09-19 22:30 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The standalone Code Generator harness can exercise planning, acquisition, generation, verification, and preview without upstream agents, but its control room is not the authenticated product surface. Testing only one surface allowed a durable run to succeed while the product UI still showed a stale working state or an unusable preview.
- **Decision:** Add a development-only, read-only Preact fixture that accepts a standalone run ID, reads the existing development run and preview projections through the Vite `/api` proxy, maps them into the same `GenerationStage` adapter, and polls only while the run is active. Configure the native preview gateway's exact embed allowlist for the fixture origin and expose a config-driven link from the standalone control room. Keep production session routes, auth, preview URL construction, and stage chaining unchanged.
- **Rejected alternatives:** Running Discovery, Content Architect, Visual Design Director, and Build Preparation for every frontend check is slow and couples a Code Generator regression to unrelated agents; duplicating the product theater in the legacy harness would create two UI contracts; accepting an arbitrary URL query parameter would bypass the preview gateway's origin and verification boundaries; auto-chaining the upstream agents would violate the explicit stage handoff contract.
- **Consequence:** A real standalone run can be inspected in the product theater without upstream setup, deterministic fixtures cover failure-state rendering, and the same adapter contract is exercised before production browser acceptance. The fixture is intentionally development-only and cannot create or mutate a production session.

## D-103 — Make the approved handoff the single generation start contract

- **Date & Time:** 2026-09-19 19:44 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Build Preparation could finish during polling while the product still showed Code Generator as locked, and its ready screen displayed invented asset/count evidence. The generation screen also exposed follow-up chat and stop controls that have no corresponding production API operation, while a generated preview could depend on a model-authored bridge script.
- **Decision:** Treat Build Preparation completion as the UI unlock event, make its primary action call the existing idempotent Code Generator start operation and navigate immediately, render only actual handoff index data, and keep the generation panel limited to durable start/retry/regenerate actions. Add a small exact-origin preview protocol module plus a response-only gateway bridge fallback; the stored artifact remains immutable and the iframe never trusts messages from an unexpected source or origin.
- **Rejected alternatives:** Requiring a refresh before generation would make durable progress appear lost; retaining fabricated evidence would misrepresent the generator input; keeping no-op chat/stop controls would promise unsupported behavior; relying only on model-generated bridge code would make preview availability depend on optional generated source; accepting iframe load or any `postMessage` would not prove the intended preview frame initialized safely.
- **Consequence:** The approved brief pair is the complete handoff boundary, users receive a continuous Prepare → Generate → Preview path, and a preview can show a truthful loaded/degraded/error state even when the optional handshake is unavailable. Follow-up editing remains a separate future contract rather than an implied UI capability.

## D-102 — Preserve bounded rejected source evidence and resolve equivalent selector forms

- **Date & Time:** 2026-09-19 16:35 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The second live run generated a valid `id="featured-projects"` motion owner, but the host compared only the CSS spelling `#featured-projects` and emitted a false motion failure. In the same repair sequence, CSS bodies rejected only for stale operation tags were stored as restricted evidence and then dropped from the next repair context, preventing reliable sibling recovery.
- **Decision:** Treat a bounded CSS ID selector as executable evidence when the owner TSX contains the equivalent static JSX `id` value. Preserve restricted response bodies alongside admitted pending bodies across source-repair iterations; they remain context-only and can never enter the candidate tree without passing normal ownership and source validation.
- **Rejected alternatives:** Requiring models to duplicate CSS selector text in TSX would create non-executable marker noise; trusting any selector-like text would weaken the contract; discarding rejected bodies would force the repair model to reconstruct unrelated files from prose and waste bounded calls.
- **Consequence:** Motion checks reason about the rendered DOM element rather than representation spelling, and bounded repair retains enough evidence to recover stale-tag siblings without broadening write authority. The live failure is fixed deterministically; no third full pipeline run is authorized or required for this contract-level correction.

## D-101 — Keep source-contract validation semantically aligned with the runtime audit

- **Date & Time:** 2026-09-19 16:15 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** A live route batch rendered approved content through literal tuple collections and indexed map values (`contentValue(item[0])`). The runtime/source audit could resolve that bounded static shape, but the Python pre-toolchain gate could not, so it emitted false blocking diagnostics and exhausted repair on an otherwise usable portfolio.
- **Decision:** Extend the host gate with a bounded balanced-literal scanner that maps exact approved IDs to tuple indexes and accepts only the corresponding mapped `contentValue(item[index])` call. Keep the repair envelope strict for each returned file, but retain unchanged bodies from a durable pending proposal so a repair is a delta over an already captured candidate rather than an unnecessarily repeated whole-unit response.
- **Rejected alternatives:** Requiring every opaque key to be repeated as a direct literal would reject readable, valid generated code; evaluating arbitrary JavaScript would be unsafe and would make the host validator too permissive; removing the pre-toolchain check would defer deterministic contract failures to a later and less actionable stage.
- **Consequence:** Generated repeated-content sections can use compact typed tuple maps without false failures, while approved content coverage remains exact, bounded, and executable. Prompt version `code_generator.repair.v11` invalidates stale repair-call caches after the contract change.

## D-100 — Gate Code Generator admission on current handoffs and worker/preview capability

- **Date & Time:** 2026-09-19 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Code Generator could accept a persisted `ready` Build Preparation pair after an approved upstream edit, queue work before a compatible worker was alive, and use one preview URL for both a Docker worker and the user's browser. These independent process boundaries produced stale portfolios, jobs stranded in the queue, or previews that passed one read-back path but were unreachable in the frontend.
- **Decision:** Recompose the approved Content Architect + Visual Design Director source reference at production admission and reject changed/unavailable upstream state. Require a fresh heartbeat with the active pipeline/release contract and explicit Node/npm/browser capability before standalone or production admission. Configure separate browser-facing and worker-verifier preview bases; preserve `preview_base_url` as the fallback. Require the authenticated frontend iframe to complete the exact-origin `preview-bridge-v1` handshake and report a timeout visibly.
- **Rejected alternatives:** Trusting the persisted Build Preparation status would preserve the stale-input race; checking only API/provider preflight would not prove a worker can execute; returning the internal Docker DNS URL would make the browser fail; accepting an iframe `load` event alone would not prove that the generated app initialized.
- **Consequence:** Starts fail early with actionable readiness/staleness details, Docker workers can verify through service DNS while users receive a resolvable preview URL, and a browser-visible preview is distinguished from an HTTP-only promotion. The worker capability receipt is intentionally model-free and non-secret; full live generation still requires the configured provider preflight.

## D-099 — Supersede D-094: preview-first acceptance may no longer certify a functionally broken candidate as `ready`

- **Date & Time:** 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5)
- **Status:** decided-implemented (supersedes D-094)
- **Context:** `docs/code-generator-repair-plan-2026-09-16.md` (F03) found that D-094's `preview_first_acceptance` flag, as implemented, downgraded *all* source-contract, build, and runtime diagnostics to advisory whenever the flag was enabled — not just the narrow generated-output-polish findings D-094 intended. Concretely: `blocking_source_diagnostics`/`blocking_runtime_diagnostics` were unconditionally emptied under the flag regardless of diagnostic content, and a runtime-verifier exception (zero browser evidence) was silently swallowed into a single advisory and still allowed promotion to `ready` with an `active_preview`, consuming success entitlement. This let a page crash, a missing required image, or a completely unverified candidate reach the same "verified" status as a genuinely working portfolio.
- **Decision:** `preview_first_acceptance` no longer affects whether source-contract, build, or runtime diagnostics are blocking; blocking status is now always computed the same way regardless of the flag (`effective_finding_severity(...) == "blocking"` for runtime findings; any source diagnostic is blocking; any non-runnable build artifact is blocking). A runtime-verifier exception is no longer swallowed — it now raises `VerificationFailure("RUNTIME_VERIFIER_FAILED", ..., owner="infrastructure")`, which fails closed to `needs_attention` without spending a source-model repair attempt. `config/app.native.toml` now sets `preview_first_acceptance = false` (matching every other overlay's already-strict default). The pre-existing, unconditional unverified-candidate-preservation path (`_store_unverified_candidate`, used whenever a blocking runtime finding is `_candidate_runtime_safe`) is untouched: a safe-but-unverified build can still surface as `candidate_preview` for inspection, but it can never become `active_preview` or reach `ready`. The narrower, unaffected uses of the flag — skipping the optional whole-site quality-review receipt requirement and skipping the optional post-repair re-review pass — are left as-is; neither one bypasses the required source/build/runtime gates.
- **Rejected alternatives:** Removing the flag/native overlay override entirely was rejected — an inspectable, honestly-labeled `candidate_preview` for a safe-but-unverified build remains useful, per the original D-094 rationale, and that path did not need to change. Keeping the blanket advisory-downgrade behavior but only for `native` deployments was rejected — the plan's premise, confirmed in code, is that a configuration toggle must never make page crashes, broken images, or absent evidence "verified," in any overlay.
- **Consequence:** A native campaign run with a genuinely broken candidate now correctly stops at `needs_attention` (or repairs, then stops if repair is exhausted) instead of silently reaching `ready`. Existing runs that were previously promoted under the old preview-first policy are not retroactively re-verified or downgraded; this only governs new verification attempts. See `CHANGES.md` for the implementing commit and regression test.

## D-097 - Use a dedicated deployment branch as the release pointer

- **Date & Time:** 2026-09-15 00:00 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-not-yet-implemented
- **Context:** The first Azure release must be easy for a beginner to identify and update, while the repository currently contains uncommitted work from another contributor. D-096 requires exact commit releases but does not require the release pointer to remain the development branch.
- **Decision:** Create a `deployment` branch only from one clean, reviewed release SHA. Push that branch after the worktree is reconciled, but deploy exact SHAs with `scripts/azure-deploy.sh deploy <commit-sha>`. Keep development changes on working branches and merge them into `deployment` only after verification.
- **Rejected alternatives:** Deploying the current dirty worktree would mix contributors' changes; deploying an unpinned moving branch would make incident diagnosis and rollback ambiguous; GitHub Actions, a registry, or a second environment would add operational complexity that is unnecessary for two or three users.
- **Consequence:** The deployment branch is a human-readable release pointer, not an automatic deployment trigger. The first branch push and SHA selection remain gated on a clean, tested release.

## D-098 - Separate server deployment from public-domain activation

- **Date & Time:** 2026-09-15 00:00 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-not-yet-implemented
- **Context:** The owner wants the Azure server and Compose stack deployed before registering or configuring `deploy.me`, but production authentication and public preview acceptance require a real HTTPS origin.
- **Decision:** Deploy the server with the future `app.deploy.me` and `preview.deploy.me` values rendered into the VM-local production configuration, validate migrations and service health through loopback checks, and defer DNS, Caddy certificate issuance, Supabase production redirects, and public browser acceptance until the domain is controlled.
- **Rejected alternatives:** Treating a public IP or self-signed certificate as production would not provide a reliable Google OAuth/HTTPS experience; blocking all server work until DNS would unnecessarily delay infrastructure validation; inventing a different hostname would diverge from the owner's selected domain.
- **Consequence:** Phase A is explicitly labeled infrastructure-ready, not publicly accepted. Phase B begins after `deploy.me` is available and ends only after external verification and multi-account browser acceptance.

## D-096 - Use one VM, Compose-managed Caddy, and one guided deployment command

- **Date & Time:** 2026-09-14 00:00 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The existing deployment shape required a first-time operator to install and configure Caddy separately, edit several production files by hand, and coordinate independent app, worker, migration, and preview commands. The project needs to stay on the current branch, be easy to repair and redeploy, and remain simple when a future engine is added.
- **Decision:** Keep the single Azure Ubuntu VM and PostgreSQL-backed Docker topology, run Caddy as a Compose service with persistent certificate volumes, bind application ports to VM loopback, and expose only Caddy's 80/443 ports. Make `scripts/azure-deploy.sh` the operator entry point for Docker installation, `.env` setup, production-config rendering, health checks, commit-tagged image builds, migrations, deployment, backup, logs, verification, and rollback. Deploy source from GitHub on the VM; do not add a registry, Kubernetes, or automatic GitHub-to-VM deployment in this phase.
- **Rejected alternatives:** Native Caddy would preserve an extra manually managed service and duplicate the proxy configuration; GitHub Actions SSH deployment would add secret and remote-state setup before the first successful release; Azure Container Apps, Kubernetes, and a registry would add concepts that do not help this small single-VM deployment; exposing internal ports would make the proxy boundary ambiguous.
- **Consequence:** A release is an exact commit SHA and the script records the last two successful SHAs locally. The ignored `.env` and `config/app.production.local.toml` remain VM-specific. Future independent engines must add a Compose service plus a healthcheck only when they need a separate process; ordinary code and profile changes use the same `deploy` command.

## D-095 — Keep Visual Design Director's frontend rendering prose-only; do not fabricate hex swatches

- **Date & Time:** 2026-09-11 17:45 +05:30 — Kiro (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** A frontend visual/UX revamp planned real color-palette swatches for the Design stage, following an older planning doc (`docs/frontend/02-agent-pipeline-and-data-contracts.md`) that described a `palette_tokens` sub-field (`visual_language contains: ..., palette_tokens`) with "concrete hex/HSL values for primary, secondary, surface, background, and accent." Direct inspection of the real, current backend contract (`agents/visual_design_director/schemas.py::VisualDesignDirectorOutput.visual_language: dict[str, Any]`, and `prompts/system.md`'s `<relationships_not_pixels>` instruction, which explicitly forbids the model from emitting "hex color values") showed `palette_tokens` does not exist in the actual Pydantic schema or the live prompt contract — it is stale documentation, not a real field.
- **Decision:** Render Visual Design Director's `visual_language` output as organized prose (a creative-thesis pull-quote, keyword chips from the real `design_keywords` array, and labeled color/typography/motion intent cards using the model's own words) rather than inventing hex values to populate swatch UI. Do not add a `palette_tokens` field to the backend schema or prompts as part of a frontend-only task.
- **Rejected alternatives:** Fabricating plausible-looking hex colors client-side from the prose description (would misrepresent unapproved, invented values as the model's actual creative decision — a fabrication risk this codebase treats seriously elsewhere, e.g. Content Architect's claim-grounding ledger); adding a `palette_tokens` field to the backend now to unblock the frontend (a real schema/prompt change belongs to a Visual Design Director-focused task with its own review, not a frontend-visuals session, and the system prompt's "no hex values" instruction reflects a deliberate choice — description in relationships/proportions, not pixel-exact tokens — that this task should not silently reverse).
- **Consequence:** The redesigned Design stage is real and richer than the old flattened-markdown-bullets view, but still text/keyword-based for color, not swatch-based. If literal color tokens become a real product requirement, that is a separate, explicit decision requiring a schema/prompt change to `visual_design_director`, not a frontend adapter workaround.

## D-094 — Make native Code Generator acceptance preview-first

- **Date & Time:** 2026-09-11 15:33 +05:30 — Kiro (configured runtime)
- **Status:** superseded-by-D-099 — the flag as implemented downgraded functionally-required diagnostics, not only generated-output-polish findings; see D-099.
- **Context:** D-085 and D-088 made generated source, quality, asset, and browser findings release blockers. In the bounded native campaign, Run 2 produced a complete runnable build but verification rejected it on a reconstructed image-policy finding, preventing the user from seeing the first preview despite an explicit instruction that generated-output defects must remain visible without failing a running site.
- **Decision:** Add `code_generator_verification.preview_first_acceptance`, default it to `false`, and enable it only in the native overlay. Under that policy, integration/quality-review failures, final-source diagnostics, build diagnostics that coexist with a complete materialized artifact, and runtime/console/network/geometry/image/content/accessibility findings are durable advisories. A runtime-verifier exception after the candidate server starts is also advisory. Immutable input admission, authorization and worker fencing, stale-source/checkpoint integrity, production-build artifact creation, candidate-server startup, storage readback, and atomic preview promotion remain blocking.
- **Rejected alternatives:** Removing verification entirely would discard ownership, integrity, build, and promotion guarantees; making fail-open behavior unconditional would silently weaken strict and hosted profiles; forcing `ready` without a materialized build or serveable candidate would create a false preview.
- **Consequence:** Native campaigns can promote the first buildable, serveable portfolio and expose its defects for inspection without spending scarce full-generation slots on output polish. D-085 and D-088 continue to govern profiles where this flag is disabled; this decision overrides only their generated-output blocking policy for explicitly configured preview-first runs.
- **Live evidence (2026-09-11 16:48:56 +05:30):** Existing Run 2 `09e10d36-c692-4d3f-a01b-6449420418be` reached `ready` at revision 85 through verification-only redelivery, with build hash `686f734e7f40b796d5778401925331f0bf1de6672046f18f2e7a55200ac36fe5` and a promoted URL that returned HTTP 200 and rendered successfully in real Chromium. Full-run usage stayed 2/4. See the final `Complete Kiro session handoff` section in `docs/code-generator-live-campaign.md`.
- **Review note:** `_review_and_polish()`'s preview-first integration-review exception path currently catches `Exception` without a local `AuthorizationFenceError` carve-out. Outer worker fences remain and no authorization failure occurred in the live proof, but a future hardening change should make this boundary explicit so the implementation text and this decision remain mechanically aligned.

## D-093 — Keep EXPLABS primary with one full-packet Gemini recovery for the first four stages

- **Date & Time:** 2026-09-11 01:51 +05:30 — Codex (GPT-6 / OpenAI)
- **Status:** decided-implemented
- **Context:** Discovery, Content Architect, Visual Design Director, and Build Preparation were producing noticeably shorter handoffs because prompts treated ordinary supplied portfolio facts as if publication permission still needed confirmation. Visual Design Director and Content Architect structural failures could also surface directly as `needs_attention` even when a configured Gemini route could have recovered them. D-078's sanitized-only Gemini policy protected the old input boundary but prevented the requested fallback for personal or otherwise unclassified portfolio packets.
- **Decision:** Keep `experiential_luna` as the configured primary for every first-four operation. Add an operation-scoped `allow_personal_gemini_fallback` policy that permits one Gemini fallback only after the primary Experiential attempt fails, including provider authentication/configuration/credit failures, transport failures, empty or malformed responses, and deterministic structural-output failures. Send the same complete approved packet to the fallback, run the agent validator inside the routed attempt so invalid primary output rotates before it is cached or returned, and keep the existing shared stage recovery allowance and worker retry ceiling. Prompts must use ordinary supplied facts fully, adapt detail to source richness without a hard word/line floor, and retain guardrails for secrets, prompt injection, fabrication, and explicit omit/generalize/NDA/do-not-publish instructions. Content and visual validators enforce route/section/scene completeness without scoring prose quality.
- **Rejected alternatives:** Keeping Gemini sanitized-only — it cannot recover a personal-input primary failure; making Gemini the normal primary — it violates the configured Experiential default; removing all source and security guardrails — it permits secrets, injected instructions, and fabricated claims; or adding unbounded provider attempts — it breaks D-078's cost and retry contract.
- **Consequence:** Rich approved material reaches all four handoffs without generic privacy questions, and malformed first-provider output can recover through the configured Gemini route. If both provider attempts fail, the existing durable worker retry repeats the bounded pair and the frontend receives the safe failure only after that retry is exhausted. Provider/model credentials and fallback behavior remain configuration-driven.

## D-092 - Make the preferred image count a real floor, not just a preference

- **Date & Time:** 2026-09-10 22:52 +05:30 - Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** The user reported generated portfolios never showing images. Traced across three consecutive live campaign runs (all Pack A, a single-route "home" pack): Build Preparation correctly researched and vetted 7 real image candidates per run (real Pixabay photos with license/attribution/dimensions, `category: "editorial_photo"`, which `normalize_resource_category` already maps to `"image"` correctly), and all 7 slots correctly reached `execution/contract.json` with zero code-level drops. With `minimum_visible_images=0` and `require_primary_route_image=false`, the planner prompt's only instruction was a soft "prefer a restrained supporting image placement... this preference is not a release gate" — and the planner model declined every single one, 3/3 times, despite real vetted material being available every time.
- **Decision:** Raise `minimum_visible_images` from 0 to 2 (matching the existing `preferred_visible_images=2`, so "preferred" becomes an actual floor the planner prompt enforces as a hard requirement) and `require_primary_route_image` from `false` to `true`, in both `settings.py` and `config/app.toml`. Left `build_image_policy_snapshot`'s `text_only_exemption` early-return path untouched — it already forces `0`/`False` unconditionally whenever a pack has zero approved image slots, so a genuinely image-less pack still degrades honestly regardless of these defaults.
- **Rejected alternatives:** Fixing this at the prompt-wording level only (making the "preferred" language stronger without changing the numeric policy) — rejected because the planner prompt already has a dedicated hard-requirement code path (`minimum_visible_images > 0`) that this simply needed to activate; inventing a second enforcement mechanism would duplicate it. Leaving it as a soft preference and instead trying to fix the *model's* creative judgment via prompt tuning — rejected because it's unfalsifiable without more live runs, whereas flipping a host-owned policy value is a single, cheap, deterministic, immediately-verifiable change.
- **Consequence:** Any pack with at least 2 approved image slots (the common case per Build Preparation's own per-section image research) now gets a real, planner-enforced image requirement, with one anchored to the primary route. A pack with fewer than 2 approved slots, or zero, still degrades correctly (fewer than the floor is a `PLAN_REQUIRED_IMAGE_PLACEMENT` validation failure only when slots exist but are under-placed; zero slots is the exemption path, unaffected). Future live runs should be checked for this working as intended before assuming it's fully proven.

## D-090 - Defer route storage-key single-source-of-truth refactor; fix the test that surfaced it instead

- **Date & Time:** 2026-09-10 15:55 +05:30 - Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** While diagnosing five stray `output/code-gen-output/` folders that looked like new live-campaign failures, direct inspection showed they were byproducts of one broken integration test (`test_code_generator_verification_worker.py::test_verification_builds_and_promotes_a_clean_candidate`), which hand-wrote its "real" route content to an invented path (`src/routes/home-4ea140588150/`) unrelated to the route's actual bare storage key (`home`), so the router-wired placeholder was validated instead of the real content. Research along the way found that `source_manifest.py`, `final_source_validation.py`, and `work_graph_compiler.py` each independently re-derive semantic-vs-bare route storage keys via their own `isinstance(plan.experience_blueprint, ExperienceBlueprintV4)` check, while `blueprint_compiler.py` computes `RoutePlan.storage_key` semantically and unconditionally once — a latent single-source-of-truth violation that *could* reproduce this same class of orphaned-content bug in a real run if those checks ever disagree.
- **Decision:** Fix the test itself (write real content to the path the scaffold actually wires, add the closed-navigation/nav-landmark markers the fixture requires) and fix a related, real diagnostics bug (see below) rather than refactoring the four storage-key call sites now. Record the inconsistency here for future evidence-triggered follow-up.
- **Rejected alternatives:** Refactor `source_manifest.py`/`final_source_validation.py`/`work_graph_compiler.py` now to consume `route.storage_key` directly instead of re-deriving it — rejected because it is unconfirmed against any real campaign failure (both live campaign-B failures were unrelated and already fixed by `22db99c`/`d9caf30`), and this campaign's own discipline (D-089's `repair_depth` non-removal) is to fix root-caused, evidence-backed defects rather than preemptively refactor unconfirmed risk right before spending scarce live-run budget.
- **Consequence:** The regression test now exercises the full build/verify/promote/screenshot path again. The storage-key inconsistency remains open; if a future live run ever produces orphaned route content again, check these four call sites first before treating it as a new defect class.
- **Follow-up (2026-09-11):** D-092's image-policy re-test (live run `74c82e9d`) put weight on `final_source_validation.py::_route_source_map()` for the first time and looked like it had actually materialized this exact risk (an apparent double-hashed storage key producing an empty route source). A fix was applied, then traced step-by-step against the real projections and found to be wrong: `_route_source_map()`'s input (`projections["site/contract.json"]["routes"]`) always carries the bare `f"routes/{route_id}"` placeholder `brief_ingestion.py` writes, never the semantic value `blueprint_compiler.py` computes onto `plan.routes` directly -- so unconditionally re-deriving the semantic segment is correct for this input, exactly matching `work_graph_compiler.py::_storage_key()` and `source_manifest.py::_route_storage_key()`, which do the same thing for the same input shape. `typescript_ast_audit.py::_route_source_path()`'s "skip if already set" guard is separately correct because it is fed a different input (`plan.routes`, genuinely pre-semanticized). The fix was reverted (file matches HEAD exactly). This closes the open question for these four call sites: they are consistent with each other given what each actually receives, not a single-source-of-truth violation. See `code generator issues.md`, 2026-09-11.

## D-091 - Surface the real issue code instead of the generic run status in terminal-failure/export evidence

- **Date & Time:** 2026-09-10 15:55 +05:30 - Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** A pre-verification plan rejection (observed live as `PLAN_SECTION_COVERAGE`) was masked in the exported `portfolio.json` as the generic `"needs_attention"` status, because `code_generator_verification.py`'s `_execute()` early-failure branches (raised before a `VerificationProjection` exists) returned `{"status": "needs_attention", ...}` with no `"code"` key, and the handler's own `reason=str(result.get("code", result.get("status", "")))` then fell back to the generic status string when building the failed-run export.
- **Decision:** Add the real issue's code to both early-failure return branches in `_execute()` so `result["code"]` always carries it through to the export `reason` and the exported `terminal_failure`/`evidence_summary.primary_issue`.
- **Rejected alternatives:** Patching `portfolio_export.py`'s `terminal_code or first_issue.get("code")` preference order instead — rejected because `terminal_code` was truthy-but-wrong (the generic status string), so that fallback never triggers; the real fix has to be upstream, where the code is dropped in the first place.
- **Consequence:** Every future pre-verification rejection (live or offline) now shows its real issue code in exported evidence, improving diagnosability for the remaining live campaign-B slots without changing any generation/repair behavior.

## D-088 - Make desktop web the release gate and keep source contracts statically provable

- **Date & Time:** 2026-09-10 03:10 +05:30 - Codex (GPT-6 / OpenAI)
- **Status:** decided-implemented
- **Context:** The reliability campaign targets browser-delivered web portfolios. Mobile-oriented planner prose must not silently add a release journey, and two live runs showed that legitimate deterministic source forms (literal object/tuple maps and conditional JSX marker attributes) were rejected because the Python pre-gate and TypeScript AST audit recognized different subsets of the language.
- **Decision:** Gate release evidence on the configured `desktop` (1440x900) and `laptop` (1280x800) journeys; retain responsive/mobile behavior and optional controls without making mobile a campaign blocker. Keep required content, interactions, assets, build, runtime, navigation, and accessibility checks blocking. Align both source validators on bounded, statically provable forms only: literal object-field or tuple collection maps and static JSX conditional markers are accepted, while computed or ambiguous values remain hard failures.
- **Rejected alternatives:** Making mobile a required acceptance viewport (would spend reliability budget on a non-target surface); disabling source-contract checks (would allow missing content and broken interactions); accepting arbitrary JavaScript evaluation (unsafe and non-deterministic); or requiring every marker and content key to appear as a literal in JSX (rejects safe, readable generated code).
- **Consequence:** Future variable briefs can produce and preview desktop web portfolios without cosmetic/mobile variation consuming the finite repair budget, while the generator still fails closed for real build, runtime, content, interaction, asset, ownership, and accessibility defects. A new authorized Linux/Azure campaign is still required before claiming an end-to-end `ready` result for this revision.

## D-089 - Reconcile Code Generator repair-budget defaults with effective configuration

- **Date & Time:** 2026-09-10 12:00 +05:30 - Codex (configured runtime)
- **Status:** decided-implemented
- **Context:** `settings.py` declared repair defaults of 3 per unit, 6 total, and 5 integration-polish rounds while `config/app.toml` effectively governed every run with 2, 4, and 3. The completed five-slot campaign showed distinct root-causable defects, not genuine repair-round starvation.
- **Decision:** Adopt the effective `config/app.toml` values as the Pydantic defaults: 2 per unit, 4 total, and 3 integration-polish rounds, retaining the existing `ge=1, le=6` bound and leaving `config/app.toml` unchanged.
- **Rejected alternatives:** Just raise the number to the older 3/6/5 values, which would not address the observed whack-a-mole defects; non-decision: retain the dead `repair_depth` field because it is written for compatibility, never read, and the real bound is `RepairBudget`.
- **Consequence:** Settings and effective configuration describe one bounded policy, and future live diagnosis stays focused on the concrete defect evidenced by the run rather than assuming more rounds would converge it. No force-`dist` path or image-retrieval change is implied.

## D-087 - Normalize typography type-step names at the schema and compiler boundary

- **Date & Time:** 2026-09-10 00:03 +05:30 - Codex (GPT-6 / OpenAI)
- **Status:** decided-implemented
- **Context:** Pack A reached source generation but its planner emitted fluid type-step names such as `type-heading`. The compiler treated that group prefix as part of the semantic name and emitted `--type-type-heading-*`, while route source used the intended `--type-heading-*` vocabulary; bounded repairs could not converge on the inconsistent compiler contract.
- **Decision:** Treat `type_steps[*].name` as a bare semantic suffix. Normalize repeated `type-` prefixes when the typed schema is validated and defensively normalize them again in the compiler for trusted `model_copy` or persisted construction paths. Emit only the canonical `--type-<name>-...` properties, and state that contract directly in the planner prompt.
- **Rejected alternatives:** Increasing the repair budget; accepting arbitrary aliases in route CSS; rewriting route source after generation; or adding a second set of compatibility properties to the trusted stylesheet. Those alternatives hide a compiler vocabulary defect or create two token systems.
- **Consequence:** Model output that echoes the CSS group prefix no longer creates undefined typography variables, while the emitted stylesheet and route prompts share one stable name space.

## D-086 - Reject inert disclosure controls before whole-site review

- **Date & Time:** 2026-09-09 23:39 +05:30 - Codex (GPT-6 / OpenAI)
- **Status:** decided-implemented
- **Context:** Pack B completed source generation but final review discovered a `Disclosure` whose panel held only an `aria-hidden` empty span; the issue surfaced too late. Review also reported a desktop column mismatch that contradicted D-076's abstract design-grid semantics.
- **Decision:** Add narrow host-owned source diagnostics for empty or aria-hidden-only `Disclosure` panels; keep this functional interaction issue blocking and instruct repairs to remove the control or use existing approved content. Mark `noninformative-disclosure` explicitly blocking. Clarify in generation and review prompts that `columns_*` are abstract spans, and map `blueprint-desktop-column-mismatch` advisory unless the real recipe or runtime contract is broken.
- **Rejected alternatives:** Increasing polish budgets; inventing panel copy; rejecting all `Disclosure` controls; or requiring a literal CSS track count for an abstract design span.
- **Consequence:** Inert controls are found during route validation and can be repaired within the existing bounded budget, while an aesthetic grid interpretation cannot consume functional acceptance.

## D-085 - Bound reliability release to serial attempts, tested layout recipes, and browser evidence

- **Date & Time:** 2026-09-09 20:31 +05:30 — Codex (GPT-6 / OpenAI)
- **Status:** decided-implemented
- **Context:** Variable brief output exposed repair-state loss, cloned generation accounting, optional component compatibility gaps, and a mismatch between model-selected layout/CSS claims and browser evidence. The authorized reliability campaign needs a bounded execution contract that can be resumed and audited.
- **Decision:** Production generation uses one authoritative, durable attempt ledger and a true serial route-batch lane; a failed batch is persisted before later siblings are considered. Pending source proposals retain the complete owned inventory, while invalid bodies stay restricted evidence until a validated candidate is accepted. The host compiler exposes three typed layout recipes with marker-bound CSS floors, and final verification independently enforces the immutable image policy through local-path, decode, visibility, frame, ancestor, and route-scoped observations. Reports consume these durable facts and distinguish source reference from browser proof.
- **Rejected alternatives:** Using a semaphore around a pre-scheduled gather (does not stop siblings or preserve failure accounting); replacing pending proposals with the latest response (loses untouched files); allowing arbitrary model CSS/templates (reintroduces selector/property drift); treating source regex matches as rendered media; and adding an unbounded repair or acquisition loop.
- **Consequence:** Route concurrency above one is fail-closed for the production lane, repair retries remain finite and resumable, optional component fallbacks cannot contaminate the trusted foundation, and a candidate cannot be promoted without evidence for the declared policy. The three recipes are additive and legacy regions keep their deterministic default.

## D-084 — Reconcile stale file-operation tags only inside bounded repairs

- **Date & Time:** 2026-09-09 13:45 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** A live route-batch response was rejected for an invalid CSS unit. A bounded repair then created the missing stylesheet, while the next repair response repeated `operation="create"` for that now-existing file and used `create` for still-missing siblings. Strict operation validation exhausted the repair budget even though every path was owned and the source body was otherwise bounded.
- **Decision:** Keep initial generation strict: `create` must target an absent file and `replace` an existing file. In repair mode only, after path ownership, trusted-file, size, import, and content checks are established, deterministically normalize each stale operation tag against the actual candidate tree. This makes a repair idempotent across partial/rejected attempts without broadening file authority.
- **Rejected alternatives:** Disabling operation validation globally (would allow accidental overwrites during first generation); blindly turning every repair into `replace` (would fail legitimate repairs that restore a missing file); adding more paid repair rounds (would hide a deterministic state mismatch and violate the bounded-call policy); and silently patching generated files outside the owned envelope.
- **Consequence:** Mixed create/replace repair responses can proceed safely across changing candidate inventories, while trusted files and ownership escapes remain hard failures. The repair prompt still instructs models to emit the operation matching `existing_files`, and the host normalization is deterministic fallback rather than model authority.

## D-083 — Make brief-driven Code Generator completion host-owned and evidence-bounded

- **Date & Time:** 2026-09-09 03:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Build Preparation emits variable, valid Markdown brief pairs, while model-authored planner identities, color tokens, and visual-review severities can vary between otherwise equivalent inputs. A planner response that is structurally close must not either fail on host-known aliases or turn subjective visual polish into an endless paid repair loop. A buildable export also needs a safe diagnostic preview when final browser verification is incomplete.
- **Decision:** Admit both the canonical and current local Build Preparation mirror shapes through one immutable brief compiler, including result-only Markdown mirrors, and validate route/section/index contracts before any model call. Canonicalize only exact host-known `(route_id, section_id)` planner identities and reserved color-token aliases; unknown or ambiguous identities remain hard validation errors. Planner attempts are bounded by configuration and record redacted telemetry plus restricted response artifacts. Effective finding severity is host-owned: functional, safety, accessibility, asset, navigation, and explicit approved-requirement failures block; geometry/polish observations remain visible advisories. After a clean build and network-safe runtime evidence, store a capability-scoped unverified candidate preview without promoting it as the active verified preview or consuming success entitlement. Keep candidate and active preview contracts separate through the API and frontend.
- **Rejected alternatives:** Trusting model-declared severity (would let cosmetic wording consume repairs or hide functional failures); fuzzy planner identity repair (could silently move content to the wrong section); accepting malformed briefs or fabricating missing sections (would violate the immutable Build Preparation handoff); treating an unverified candidate as the active preview (would misrepresent runtime evidence); and adding an unbounded planner/repair loop (would violate the live-call budget).
- **Consequence:** The development harness can consume the two current valid packs and older canonical pairs without format-specific code paths, while malformed packs are rejected deterministically. The release decision is based on blocking evidence rather than subjective score thresholds, planner failures retain traceable diagnostics without persisting raw responses in durable receipts, and users can inspect a buildable but explicitly unverified candidate separately from the last verified preview. The configured planner and repair limits remain the upper bound for live calls.

## D-082 — Retire the legacy static pipeline shell

- **Date & Time:** 2026-09-09 01:20 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The canonical Preact product frontend is now built and served at `/app`, while the former static Discovery/pipeline shell at `/dev` duplicated the product surface and could be selected as an `/app` fallback.
- **Decision:** Remove the legacy `index.html`/`app.js`/`app.css` shell, its `/dev` route, and both bootstrap fallbacks that imported it. `/app` is Preact-only and returns a clear 503 when the Preact bundle is unavailable. Keep the separate Build Preparation diagnostic and Code Generator control-room routes/assets unchanged and independently gated.
- **Rejected alternatives:** Keeping `/dev` as a compatibility alias (would leave the retired UI reachable); retaining the silent `/app` fallback (could hide a missing product build and reintroduce two competing frontends); deleting the shared static directory (would remove Preact build output and the Code Generator frontend).
- **Consequence:** Native/local requests to `/dev` and the removed legacy assets return 404, while `/app` and the Code Generator control room continue to serve their intended frontends. A frontend build is now an explicit prerequisite for `/app`.

## D-081 — Release a merged Generate & Preview stage in `/app`, superseding D-063's boundary

- **Date & Time:** 2026-09-08 23:00 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** D-063 (2026-09-04) deliberately ended the authenticated `/app` product at approved Build Preparation, with Code Generator and Preview "accessible only via developer routes/APIs until explicitly released." The owner has now explicitly asked for a production option to generate the portfolio and preview it from `/app`. A near-complete implementation of this had briefly existed (`f9e8eef`, `9c27a69`) before being deliberately removed (`389fa28`) as premature; that removed code used a since-changed `active_preview` field shape (`origin`/`base_url`/`path` instead of the current `host`/`url`/`route_ids`/`route_paths`) and a separate `PreparationStage.tsx` since superseded by D-079's `BuildPreparationStage.tsx`.
- **Decision:** Add a fifth, explicit `generate` stage to `JourneyStageId`/`AppState`, gated on Build Preparation reaching `complete`. It calls the existing, previously-unexposed production Code Generator session API (`GET/POST .../code-generator[, /start, /regenerate]`) through a new `adaptCodeGenerator` adapter (`data/adapters/generation.ts`) and a new `GenerationStage` component, following the exact polling/mutation/dispatch pattern already established for Build Preparation. Generate and Preview are merged into one stage, not two — the rail's previously-decorative, permanently-locked "Preview" tile is removed rather than left as a dishonest "coming soon" placeholder. The stage's own preview panel (route selector, mobile/tablet/desktop/fit viewport buttons at the documented 390×844/768×1024/1440×900 sizes, refresh, open-in-new-tab, a sandboxed `iframe`) reuses the exact `postMessage` bridge protocol (`preview:init`/`preview:ready`, version `preview-bridge-v1`) already live-verified in the separate developer harness. A `needs_attention` result with a retained `active_preview` (the backend always keeps the last verified preview visible during a failed regeneration) shows both the attention panel and that last-known-good preview; without one it shows only the attention panel. `product-boundary.test.ts`'s contract assertion is flipped to require the `/code-generator` endpoint is now present, since its prior absence was this decision's own boundary, not an accident to keep guarding against.
- **Rejected alternatives:** Rebuilding the stage from scratch instead of recovering `f9e8eef`/`9c27a69` — rejected; the recovered code already matched the current API contract's operation names and needed only field-shape adaptation, not a redesign. Keeping Generate and Preview as two separate rail stages — rejected as the user asked for one "preview the generated portfolio" option, and the backend itself exposes only one stage's worth of session state (no separate preview-approval endpoint exists to justify a second stage). Wiring the already-existing `/code-generator/retry` production endpoint into this UI — deferred; every architecture doc still describes production as start/regenerate only, and resolving that doc/code mismatch is a separate decision from this release.
- **Consequence:** `/app` now offers a complete Discover → Content → Design → Prepare → Generate & Preview journey with no hidden downstream request beyond this stage. The developer harness (`/dev/code-generator-development`) remains a separate, richer diagnostic surface (unverified-candidate preview, source inspection, retry) not duplicated here. Code Generator's own reliability/cost behavior is unchanged by this decision (see the same session's Code Generator repair/cache-key/round-budget fixes, logged separately in `CHANGES.md`).

## D-080 - Make Experiential organization telemetry explicitly scoped

- **Date & Time:** 2026-09-08 16:05 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The live inference lane was healthy, but the usage reconciler was probing the hosted web origin and omitting the organization identifier required by Experiential's management usage endpoints. The resulting 401/422 responses added noise and could never produce authoritative wallet or daily usage observations.
- **Decision:** Resolve the management host from provider-neutral capacity configuration (the configured inference URL with /v1 removed, defaulting to the documented API host). Make organization-scoped usage reads conditional on an optional org_id_env; when absent, skip those calls rather than inventing an identifier. Always use the authenticated non-secret key list when available, and pass only an explicit listed key ID to the effective-limits endpoint. Keep local PostgreSQL attempt/cost telemetry authoritative until an org ID is supplied.
- **Rejected alternatives:** Reusing the platform web origin (wrong management surface); passing project_scope = "organization" as if it were a real identifier (not an org ID); guessing an org from a key prefix or generic event/request ID (unsafe attribution); and treating failed usage reads as zero usage (would under-report spend/quota).
- **Consequence:** A deployment can opt into provider usage rollups by setting the non-secret EXPLABS_ORG_ID value without changing agent code or exposing credentials. Missing account scope is observable through bounded debug logging, while key limits and all locally persisted request telemetry continue to work.

## D-079 - Integrate Build Preparation and expose complete stage outputs in `/app`

- **Date & Time:** 2026-09-08 14:20 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The authenticated Preact product stopped after Visual Design even though the durable Build Preparation service and its explicit start/regenerate APIs were already implemented. The review cards also presented only selected fields, making it impossible to copy the complete persisted response for Discovery, Content Architect, Visual Design Director, or Build Preparation.
- **Decision:** Extend the provider-neutral `/app` journey with a fourth, explicit Prepare stage. The stage reads the existing Build Preparation GET/start/regenerate contract, requires approved Content and Visual Design, polls only while the durable job is working, maps unknown/stale/failed states to safe UI states, renders the two Markdown briefs and bounded scope/resource summaries, and never starts Code Generator or Preview. Each stage response now carries a safe `agent_output` projection loaded from the successful `AgentRun.output_payload`; the projection preserves unknown nested agent fields while removing only explicit transport/security wrappers. A contextual right rail provides selectable, clipboard-backed `Copy JSON` controls for all four stages, including a DOM fallback when Clipboard API permissions are unavailable.
- **Rejected alternatives:** Auto-starting Build Preparation on Design approval; exposing Code Generator or Preview controls before their separate product release; reconstructing copied JSON from visible cards or a field allowlist; adding a download button to the normal creator flow; and replacing the existing auth/bootstrap or API client.
- **Consequence:** `/app` now ends at a truthful generator-ready handoff with no hidden downstream request. The output rail remains read-only and refresh-safe, preserves complete future agent fields, and keeps provider/model/job internals out of the copyable public projection. The existing `/dev`/technical Build Preparation and Code Generator surfaces remain separate.

## D-078 — Route the first four agents through a provider-neutral free-tier policy

- **Date & Time:** 2026-09-08 05:23 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The first four stages need Experiential Labs GPT-5.6 Luna as the safe default without normal calls falling back to `OPENAI_API_KEY`, while sanitized lightweight work may use three independent Gemini Free Tier projects. The prior retry/cost design could multiply transmissions across SDK, provider, worker, and agent layers, and there was no durable cross-user quota/attempt ledger.
- **Decision:** Keep agent logic on the existing `ModelClient` boundary and resolve provider/model/profile from `config/models.toml` operation routes. Personal or otherwise unclassified first-four input is Luna-only through `EXPLABS`; explicitly sanitized/synthetic lightweight Discovery questions and Build Preparation may use Gemini 3.5 Flash Lite, while sanitized higher-complexity fallback uses the configured explicit Gemini Flash model. Every operation receives one durable normal/recovery budget (one normal plus one recovery for Discovery/Build Preparation; up to three normal plus one recovery for Content Architect/Visual Design Director), with SDK retries disabled and worker redelivery capped at two executions. Persist provider/model/alias/operation/attempt/fallback/token/cost/error/request-ID and quota-window records in PostgreSQL before transmission; reserve capacity at 80% of observed/configured ceilings, reconcile provider observations under an advisory lock, and leave unresolved reservations on acceptance-uncertain timeouts. Cache identity is resolved after the concrete route and policy snapshot, and a successful fallback is stored under its actual route identity. Frontend errors expose only safe provider/operation/support metadata.
- **Rejected alternatives:** Directly replacing the current OpenAI adapter; using `OPENAI_API_KEY` as a hidden first-four fallback; blind Gemini key round-robin; provider SDK retries plus agent/worker retries; counting the `$1` card verification as wallet credit; and relying on model names or latest aliases in agent code. These either violate the privacy/cost boundary, bypass legitimate quota, or make attribution and replay safety impossible.
- **Consequence:** Provider/model changes are configuration-only, Luna was live-verified through the configured Experiential endpoint with an `EXPLABS`-attributed request, and a sanitized live probe succeeded on `GEMINI_1` using the explicit configured model. The Windows runtime now declares `tzdata` so Pacific daily quota windows are durable on hosts without an IANA database. The policy is ready for future providers without changing stage business logic.

## D-077 — Implement PLAN.MD's Step 1 in full plus bounded generation-time authoring fixes; defer the Step 3 component rewrite and Steps 5/7/8/9

- **Date & Time:** 2026-09-07 12:10 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** A second externally authored reliability handoff (`PLAN.MD`, superseding the plan D-076 partially addressed) diagnosed 13 confirmed generation/verification defects from repository inspection, 8 saved exports, and a fresh Chromium inspection of the latest `dist` — no implementation changes or paid calls made by its author. It proposed a 9-step implementation order spanning scaffold truthfulness, deterministic shell/navigation, three new trusted responsive-layout components (`RegionLayout`/`ReadableCopy`/`MediaFrame`) with a new `layout_spec` blueprint field, unified geometry/motion/content contracts, context-size reduction, candidate isolation/attempt-accounting/export forensics, campaign-wide budget persistence, and default brief-set selection for the dev harness. The owner's explicit instructions for this pass: fix the generator so it reliably works, prioritize the generation side over the validation/observability side, and add automatic `npm run build` capability to exported projects, within a stated $4 remaining live-evaluation budget.
- **Decision:** Implemented Step 1 in full (package.json `dev`/`preview`/`check` scripts; `typecheck` now runs both `tsconfig.app.json` and `tsconfig.node.json` instead of the root config's `files: []`, which checked nothing; `@types/node` + `tsconfig.node.json` `types: ["node"]`; a real latent `ROUTES` typing bug the new typecheck immediately caught; README.md). Implemented the generation-side authoring fixes behind 5 of the 13 confirmed findings without adopting the proposed new components/schema fields: (finding #4) threaded Content Architect's approved `public_content_manifest.nav` into `generation_contract.py` so route_compose can render real `data-navigation-target` links, previously impossible since nothing exposed that data to generation at all; (finding #9) added a bounded, non-interpreting fallback in `source_validation.py` for a statically-known `array.map(id => contentValue(id))` content binding that `scripts/audit-source.mjs`'s real TS-AST checker already accepted but the stricter Python pre-gate rejected first; (finding #8) gated `source_validation.py`'s motion-beat checks behind "no `pattern_id`" — a trusted-pattern beat's entire implementation lives in `motion.css`/`SharedSystems.tsx`, files never in a section's own owned source, so the prior checks were unsatisfiable by construction for every correctly-implemented trusted beat; also fixed `reveal-clip-lines`'s catalogue description, which falsely advertised a `load` trigger; (finding #7) clarified in `planner.md`/`repair_source.md` that `width_ratio` selectors must be true peers (never a region container against its own child) and that ratio direction is `source/target`; (finding #3/#6) added explicit prompt guidance pairing `aspect-ratio` with `min-width: 0`/`max-width: 100%`, and anchoring breakpoints at the exact configured 768px/1440px verification widths instead of an arbitrary round number. Bumped the touch-target minimum 36px -> 44px per the plan (config, runtime_verifier fallback, prompt prose). All fixes are unit-tested (4 new/extended regression tests) and then independently confirmed via one fresh live run (see Consequence).
- **Rejected alternatives:** The full Step 3 rewrite (three new trusted components, a new `layout_spec` schema field, wiring into `design_realization.py`'s region compilation) — rejected for this pass as a materially larger, riskier lift than the confirmed defect required; a bounded prompt-level fix (peer aspect-ratio/min-width pairing, exact breakpoint anchors) address the same live-confirmed symptom (a 390px hero measuring ~410px wide) without a new component surface to test and maintain. Full deterministic navigation (deleting the model call, generating the entire shell/nav from Python) — rejected in favor of keeping the existing model call and only closing the specific data gap that made `data-navigation-target` impossible; this is a smaller, safer change with the same observable effect for the confirmed defect. Steps 5 (context-size reduction), 7 (candidate isolation/attempt accounting/export forensics), 8 (campaign-wide budget persistence), and 9 (dev-harness default brief-set polish) — deferred per the owner's explicit instruction to prioritize generation correctness over validation/observability/cost-accounting work this pass; none of them were blocking the live acceptance test.
- **Consequence:** `uv run pytest tests/unit/agents/code_generator/`: 260 passed, 1 pre-existing failure confirmed present on a clean `git stash` tree (unrelated `test_v2_architecture.py` materialization test, not touched). One fresh live run against the canonical brief pack (`01-31-04-09-94ae4a9c`, run `7df7af45-bcf6-41ad-9d63-ce5271df9f0a`) reached the deepest state this multi-day engagement has recorded: `generate: succeeded`, then verification's DOM/runtime checks, one bounded repair round, and a full whole-site quality re-review, all without a single navigation, content-binding, motion, or touch-target diagnostic — confirmed by inspecting the real generated output directly (`data-navigation-target="home"` present with a resolved `publicRouteUrl(...)` href; every generated `aspect-ratio` rule paired with `min-width: 0; max-width: 100%`; breakpoints anchored at exactly `min-width: 768px`/`1440px`; `--size-control: 2.75rem` = 44px; a `<Reveal>` trusted-pattern beat present with no hand-authored duplicate animation). The run ended `needs_attention`, not `ready` — the whole-site reviewer's sole blocking finding was a genuine composition judgment (`.selected-work__image { aspect-ratio: 1/1 }` rendered as "a prominent square block" instead of the blueprint's "narrow tactile edge accent"), unrelated to anything in this pass's scope. Separately observed and NOT part of this defect set: the hero's live-fallback image search (Pixabay, triggered because the pinned candidate 400'd) returned a thematically unrelated result (gold trophy statues for a UI/UX portfolio) — a resource-search-relevance issue in `resource_scout.py`'s fallback path, logged in `code generator issues.md`, not fixed this pass. Two Windows-specific operational findings from running this live test, also logged: an `EPERM`/`ENOTCACHED` failure the first time, root-caused to `@types/node`'s new transitive `undici-types` dependency never having been warmed into this project's dedicated offline npm cache (`.workspace/npm-cache`, separate from npm's default global cache) — fixed by warming it once, a one-time operational step this decision's Step-1 changes require; and a `GENERATION_SWAP_FAILED` caused by the operator's own shell still holding the run's `repo/` directory as its working directory, which Windows treats as a lock on renames/deletes into that path — not a pipeline defect, but worth a scaffold/harness reminder to always leave workspace directories before triggering a build.

## D-076 — Reject the proposed v6 execution-contract rearchitecture; fix the region/distinctive-move runtime checks' actual semantics instead

- **Date & Time:** 2026-09-06 21:15 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** An externally authored reliability-repair plan (no live calls or repo changes made by its author) proposed a versioned `ResolvedExecutionContract` v6 rearchitecture — a new blueprint schema, centralized version dispatch, worker-release fencing, and a new review order — to fix confirmed generation/verification defects. Its "confirmed problems" list was verified against actual code first rather than trusted; several matched this project's own still-open `code generator issues.md` frontier almost exactly. Five fresh live runs that evening (see `code generator issues.md`) surfaced the real, specific defects underneath those claims: `RuntimeVerifier`'s region-width and readable-measure checks used `getBoundingClientRect().width` (the CSS border box) as the numerator, which for any auto-width block-level region with padding-based visual inset — the extremely common "full-bleed section, inset via padding" pattern confirmed in real generated CSS — is structurally guaranteed to read a 1.000 ratio regardless of design quality; the region column-count check demanded an exact `grid-template-columns` track count matching an abstract `columns_mobile/tablet/desktop` field with zero documented semantic anywhere in prompts, schema descriptions, or this file; and `DistinctiveMoveRuntimeCheckV1` never carried the blueprint's own `runtime_marker` through, so a CSS-property check could only ever look at `source_selector` itself even when a well-organized implementation reasonably scoped those properties to a nested marked element instead.
- **Decision:** Do not adopt the v6 rearchitecture. This project's real history is ~50 targeted, evidence-driven live-bugfix commits, not big-bang rewrites, and no DECISIONS.md entry supported the scope of a new contract/schema/worker-fencing generation. Instead: (1) region width/measure checks now subtract the region's own computed inline padding from `rect.width` before computing a ratio, measuring the content box instead of the border box. (2) The region column-count check now only requires that "is multi-column" (`computedColumns > 1`) agrees between observed and expected, never an exact count — `RUNTIME_REGION_WIDTH_RATIO` already independently verifies the real visual-correctness signal. (3) `DistinctiveMoveRuntimeCheckV1` gained an optional `runtime_marker: str = ""` field, threaded from the blueprint through `design_realization.py`; the runtime check now prefers the marker-scoped element for `required_css_properties` when one is configured, falling back to `source_selector` itself otherwise (unchanged default). All three fixes are live-confirmed via real Playwright-driven tests proving both the before-bug and after-fix behavior, not just code reading; (1) is additionally confirmed via a live run showing `RUNTIME_REGION_WIDTH_RATIO` completely eliminated from its diagnostics.
- **Rejected alternatives:** The v6 `ResolvedExecutionContract` rearchitecture itself — rejected as disproportionate to the actual defects found, none of which needed a new contract version, schema, or worker fencing to fix correctly. Demanding an exact `grid-template-columns` track count matching `columns_desktop` literally — rejected because a considered, good-looking asymmetric 2-track split is a legitimate implementation of an "8/12-column" abstract design-grid span, and no prompt or schema documentation ever told the model otherwise. Leaving the region width/measure checks on the border box and instead trying to make the model always add an explicit `max-width` — rejected because the bug is in what the check measures, not what the model generates; padding-based inset is standard, correct CSS practice.
- **Consequence:** `code_generator`-scoped test count rose from 255 to 272 (all new tests real-browser-driven, not fixture mocks). Live-confirmed across 5 fresh runs the same evening: the pipeline moved from crashing before verification ever ran (a separate fragment-href crash fix, same session) to reaching real DOM/runtime layout checks cleanly, with the width-ratio false-positive confirmed gone. A genuine remaining architectural tension was found and deliberately left open rather than rushed: this project's 3 fixed checked viewport widths (mobile/tablet/desktop) don't necessarily align with a model's own freely-chosen responsive CSS breakpoints, which real designs correctly tune to when a specific layout starts looking cramped rather than to a rigid three-tier system — logged in `code generator issues.md` as the next real design decision needed, not guessed at under session-end time pressure.

## D-075 — Make Content review approvable and combine the explicit Discovery handoff

- **Date & Time:** 2026-09-06 13:15 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** A live Content Architect result reached `content_review` even though its approved home route referenced a certification claim whose publication status was still `pending`; the approval endpoint therefore rejected the result only after the user had reviewed it. The authenticated UI also required a second confirmation after the user had already chosen to approve Discovery, and users needed a safe, copyable view of each persisted final agent artifact.
- **Decision:** Reuse the approval endpoint's deterministic public-scope check inside Content Architect before a result can enter review. If the assembled result is incomplete and one of the existing maximum three calls remains, use that slot for one targeted `integrate_content` correction; never increase the call ceiling or promote pending/blocked claims merely to pass. If correction remains impossible, fail before review. For already-persisted legacy-invalid drafts, one Content approval click explicitly starts a targeted revision and requires review of the changed result before approval. One Discovery UI gesture now calls the existing Discovery approval endpoint and then the existing Content start endpoint in sequence; this remains user-triggered explicit orchestration, not background auto-chaining. Copy controls expose a field-whitelisted final-artifact projection and exclude intake, authentication, and job metadata.
- **Rejected alternatives:** Removing the approval gate (would publish unsafe/incomplete content); marking the pending certification claim approved automatically (would conflate source presence with publication authorization); adding an unbounded repair loop or fourth call (higher cost and less predictable latency); auto-approving a corrected legacy draft (the user must review changed public copy); introducing a new combined backend endpoint (unnecessary duplication of already-idempotent explicit stage endpoints).
- **Consequence:** New Content reviews are approval-ready by construction within the existing cost ceiling. Existing affected sessions self-route into one bounded safe revision instead of repeating the same 409. Discovery-to-Content needs one user decision while preserving explicit stage boundaries. Discovery, Content, and Design review surfaces provide copy-ready final JSON; the existing Build Preparation diagnostic retains its JSON copy control.

## D-074 — Live-testing iteration closes 8 more real gaps; failed runs now export their output

- **Date & Time:** 2026-09-06 02:35 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Following D-072's five acquisition/planner fixes, continued live-testing iteration (per the user's explicit "keep going until fixed" instruction) surfaced 8 further real, distinct bugs, each found only by running a genuine live attempt and tracing the exact failure: (1) the review/repair layers had no concept of a non-required resource placement with an honest `generated_local` fallback, blockingly demanding a real photo that was never required; (2) `source_validation.py`/`typescript_ast_audit.py`'s distinctive-move CSS selector match required an *exact* string with zero tolerance for a legitimate ancestor-scoping prefix (`#hero [data-region-id=...]`), rejecting genuinely-correct CSS every repair round; (3) the planner's shadcn/color-collision retry (D-071) didn't always land in the existing 2 attempts; (4) a single response listing the same file path twice with two nearly-identical bodies (the model revising its own answer) exhausted the repair budget; (5) `repair_source.md` had no relative-import-depth guidance for section files, only for the route composer, so a repair round used one `..` segment too many; (6) `Reveal`/`StaggerGroup` (this engagement's own motion-pattern catalogue components) had no way to accept a marker attribute onto their own wrapper, so a CSS selector combining `data-motion-ready` with a resource marker could never match; (7) `planner.md`'s own prose describing 2 trusted motion patterns ("easeOutCubic-family", "easeOutExpo-family") read close enough to a literal CSS value that the model copied it directly into a strictly-validated `easing` field; (8) the same real DOM/runtime defect, caught by more than one viewport's journey, was reported as several identically-fingerprinted diagnostics inside one already-large repair bundle, adding no information and making the ask look larger. A live run subsequently reached final DOM/runtime verification for the first time with `generate` fully succeeded (previously undocumented milestone) and produced this project's first real screenshots of a generated portfolio, confirming a genuinely good-looking, coherent site is achievable. Separately, the user explicitly asked that `output/code-gen-output/` preserve a run's source/build/screenshots even when the run ends in `needs_attention` or `failed`, not only a promoted `ready` run.
- **Decision:** Each of the 8 findings got a narrow, evidence-driven fix at its exact root cause (prompt guidance where the model lacked information already available in context, deterministic host-side normalization/canonicalization where a mechanical mistake was cheaper to fix than to reject, or a corrected validator where the check itself was too strict) — see `code generator issues.md` for the full per-finding table. For the export request: added `export_failed_run()` to `portfolio_export.py`, a best-effort sibling of `export_portfolio()` needing only a run id and whatever the workspace already has on disk (no promotion-only state). Wired into the two central failure choke-points — `code_generator.py`'s shared `_needs_attention()` (covers plan/acquire/generate failures) and `CodeGeneratorVerificationHandler.execute()` (covers verification failures) — both wrapped in try/except, never affecting the actual failure-reporting flow.
- **Rejected alternatives:** Raising `max_repair_rounds_total`/`max_repair_rounds_per_unit` to work around the repair-budget exhaustions in (2) and (4) — rejected per the same standing D-067/D-068 reasoning: the actual defects were a too-strict validator and a redundant duplicate, not insufficient rounds, and fixing the real cause needed no budget change. Silently picking a specific `cubic-bezier` curve to "correct" (7)'s ambiguous prose — rejected in favor of `ease-out` (an always-valid, always-safe simple keyword) since the model never gets a chance to select a bespoke curve for a pattern-driven beat anyway (the pattern's real curve is fixed in `motion.css`). A single combined `execute()`-wrapping choke-point for the export feature across all four stage handlers — rejected; plan/acquire genuinely produce no source worth exporting, so only the two handlers that can meaningfully have a `repo/` tree (generate, verify) needed wiring.
- **Consequence:** 261 code_generator-scoped unit/integration tests pass (up from 232 at D-068), zero new failures beyond the 5 confirmed-pre-existing ones tracked in `code generator issues.md`. Two consecutive fresh live runs reached `generate: succeeded` → final verification, the deepest and most consistent this engagement has gone; one produced real, genuinely good-looking screenshots (`output/code-gen-output/01-56-06-09-2026-0db8503e/screenshots/`). A full clean `ready`/promoted pass was still not reached this session — the remaining failures are a missing keyboard-accessible disclosure component and a `SOURCE_CONTENT_KEY_MISSING` content-binding gap, both logged in `code generator issues.md` as not yet investigated. The failed-run export is confirmed working against real past failure data (source, dist, and screenshots all present) and via 4 new automated tests; one real run's auto-export could not be directly observed live because its worker process had already loaded the pre-fix module before the fix landed on disk (expected Python behavior, not a bug — a fresh run auto-exported correctly).

## D-073 — Make foreground agent jobs recoverable and user-observable

- **Date & Time:** 2026-09-06 01:19 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The API could accept a request while the worker was stale or older generator work occupied the single model lane; the browser had no safe lifecycle evidence and could spin indefinitely; a valid long pasted resume could also be returned as `NEEDS_DETAILS` with no questions.
- **Decision:** Keep one global model-generation lane but rank Discovery, Content Architect, Visual Design Director, and Build Preparation jobs as foreground work; requeue expired leases before claims and clear their lease tokens to fence late completions; expose allow-listed lifecycle metadata and a local metadata-only trace/download path; postprocess contradictory substantive Discovery output into two deterministic questions, including long unstructured messages. Keep cache scope, result validation, and provider boundaries unchanged. Treat an identical completed Discovery start as a stored-result/idempotent response.
- **Rejected alternatives:** Starting model calls from the API (breaks the durable worker boundary); adding an unbounded retry/second lane (increases spend and concurrency); logging request/response bodies (privacy risk); making another model call to repair the contradictory cached result (unnecessary spend); sharing results globally across users (cross-user contamination).
- **Consequence:** Fresh visible-agent work can reclaim an abandoned lane; users see actionable waiting/retry/stop states and can hand off a safe trace; repeated results remain cheap and privacy-safe; the deterministic fallback keeps full resumes actionable without a second provider call.

## D-072 — Root-cause resource-acquisition failure to a stale pinned URL, not a wrong-field bug; bound the fallback and stop repeating unfixable findings

- **Date & Time:** 2026-09-05 21:15 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Two fresh live runs (`b52330f2-…` `PLANNER_OUTPUT_INVALID`; `93d4d3c4-…` `INTEGRATION_REVIEW_UNRESOLVED` after all 5 polish rounds) were traced to root cause via persisted ledger data rather than patched narrowly, per this session's established methodology. The deepest trace found something bigger than either symptom: across 14 sampled real-run ledgers, resource bindings were `"fallback"` disposition (no real local file materialized) in 100% of cases for 7 of the 14 runs, and a majority in most others — not a rare edge case, the dominant acquisition outcome. Root cause traced to `_pixabay_candidate()` (`agents/shared/image_retrieval.py`) preferring Pixabay's `imageURL` field, which Pixabay only serves to specially-approved accounts. **A direct empirical test against the live Pixabay API corrected the initial hypothesis before it was trusted**: a fresh search's `largeImageURL` already downloaded successfully (HTTP 200) with the currently-configured key, even before any fix — the "wrong field" theory alone did not explain the observed failures. Tracing the exact pinned URLs recorded in the eligible pack's own brief-envelope JSON (`resources[*].candidates[*].url`, all shaped `https://pixabay.com/get/<hash>_1280.jpg` — the same shape as a fresh `largeImageURL`) and re-requesting them directly confirmed they now 400 live, while a brand-new search for equivalent images succeeds. The real defect: **Build Preparation's D-060 pinned candidate URLs can go stale (signed/time-limited) between pin time and Code Generator's later acquisition**, and the pinned-candidate path (`jobs/handlers/code_generator.py`) had no fallback — any materialize failure went straight to `_fallback_receipt()`. Separately and independently: the mid-generation polish loop (`generation_orchestrator.py::_review_and_polish`) rebuilds blocking findings fresh from each round's review with zero memory of prior rounds, so an owner whose finding is structurally unfixable (confirmed via ledger inspection: `RESOURCE_BINDING_UNAVAILABLE` at round 1, `RESOURCE_PLACEMENT_MISSING` — same root cause — at round 4) gets an identical doomed repair call every remaining round; the model's own `cannot_complete` `safe_reason` was also being silently dropped from logs, making this expensive to diagnose. Finally, the planner's CSS-length validator already retries once with the validation error appended as corrective feedback, and the model still wrote `"sixtyrem"` on both attempts of the same real run — more prompting had already been tried and had already failed.
- **Decision:** (1) `_pixabay_candidate()`: drop `imageURL`/`fullHDURL` from the field-preference chain (both Pixabay-documented approved-accounts-only fields), use `largeImageURL`/`webformatURL` only — correct defense even though it wasn't the direct cause of the observed failure. (2) The acquisition handler's pinned-candidate branch: wrap its `adapter.materialize()` call in its own try/except; on failure, fall through into the existing live-search-and-select code as a single bounded fallback attempt (never a loop), preserving all existing required/no-fallback hard-fail semantics unchanged for when both attempts fail. (3) `_review_and_polish`: track an owner→exhausted-finding-codes map scoped to one run; skip an owner for a round only when *every* current blocking code already returned `cannot_complete` before, so a genuinely different finding for the same owner still gets its fair first attempt. (4) The `cannot_complete` log call now includes the real `result.mode` and, when applicable, `result.cannot_complete.safe_reason`, instead of a hardcoded label and no reason. (5) `_validate_source_sizes()` and the 5 duplicated token-name-casing validators in `development_schemas.py` now normalize a deterministically-fixable mechanical mistake (a spelled-out number before a CSS unit; mixed-case token identifiers) before the existing reject-check runs, rather than only rejecting — a genuinely unparseable value still rejects exactly as before.
- **Rejected alternatives:** Extending the peer session's new full-result `StructuredResultCache` (D-069) to Code Generator — rejected: its whole-result cache would silently return a stale result on a repeat attempt against the same pack, defeating the actual point of this session's live verification testing. Wiring `BudgetedModelClient` (D-070) into production Code Generator — rejected as disproportionate plumbing for what the user asked for; its `spent=` reseed pattern implies real cross-job persisted-total infrastructure this task doesn't need, when reusing its pure pricing-rate math against already-captured usage logs achieves the same practical budget-tracking goal. Reordering the pipeline so acquisition runs before planning — rejected: planning selects which slots matter out of a broader catalogue, and acquisition targeting only referenced slots is intentional and efficient; the actual defect (a pin going stale between two already-correctly-ordered stages) doesn't require reordering to fix. A proactive compile-time filter dropping every resource placement pointing at a currently-fallback binding before generation ever sees it — considered, then rejected in favor of the fallback+dedup combination above: given fallback was found to be the *dominant* outcome pre-fix, aggressively dropping placements would have suppressed real images across most sections rather than fixing the actual acquisition defect underneath them.
- **Consequence:** All five fixes are free/deterministic and fully tested (unit + integration, zero API cost) — 251 passing in the `code_generator`-scoped suite, plus 5 confirmed pre-existing failures (verified via `git stash` to fail identically without any of this round's changes; not caused by this work). The pinned-fallback fix is directly confirmed via a real integration test asserting exactly two materialize attempts (pinned, then live-search) and an `"admitted"` final disposition. Live verification against the existing eligible pack — to confirm the fallback rate actually drops and a run reaches a clean `ready` status — is the next step, tracked in `code generator issues.md`, not yet completed as of this decision.

## D-071 — Catch a silent token-collision corruption bug; sharpen two repair diagnostics with concrete evidence

- **Date & Time:** 2026-09-05 19:30 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Live testing of D-068's fixes surfaced three further real bugs across 6 fresh live runs. (1) The model transcribes an opaque hash-like content-key suffix with a one-character typo and repeats the identical typo across every repair round, exhausting the mid-generation repair budget on a copy mistake the generic `SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING` diagnostic gave it no way to self-correct. (2) `SOURCE_BLUEPRINT_MOVE_MARKER_ONLY` (final-verification distinctive-move CSS check) had a generic message, unlike its mid-generation sibling `SOURCE_ROUTE_BATCH_DISTINCTIVE_MOVE_INVALID` which already names the exact selector/properties — the final-repair model reported `cannot_complete` on it 3 rounds running. (3) A genuine silent-corruption bug: a raw color token and a shadcn theme binding slot sharing the same literal name (both commonly "accent", one of the fixed shadcn slot names) compile to the identical `--color-accent` CSS custom property; the alias, emitted second in `_compile_v4_tokens`, silently overwrites the real color with no error anywhere in the pipeline — it only surfaced as a whole-site quality-review finding after a full, costly generation pass, and even then only as an opaque "semantic-token-alias-collision" description with real scores of 4/4/4/4/4 lost to one avoidable finding.
- **Decision:** For (1) and (2), added near-miss/concrete-evidence detection to the respective diagnostic messages (`source_validation.py`'s `_near_miss_content_key`, `typescript_ast_audit.py`'s enriched `SOURCE_BLUEPRINT_MOVE_MARKER_ONLY` message) so the repair model gets the same actionable specificity its sibling checks already had. For (3), added the identical collision check at two layers: `DesignTokenSystemV4`'s own Pydantic validator (`development_schemas.py`, right beside its existing sibling check that binding values reference approved colors) — catching it the instant the planner responds, confirmed live rejecting a real "accent"/"accent" collision on the very next attempt — and `token_compiler.py`'s `_compile_v4_tokens` as a defense-in-depth backstop for any blueprint reaching compilation without re-validating (e.g. via `model_copy`, which does not re-run validators). Also added explicit `planner.md` guidance naming the exact failure mode, since the model repeated the identical collision on the live attempt immediately after the validator started rejecting it — the validator prevents the corruption either way, but the prompt guidance reduces how often the whole plan has to be regenerated for it.
- **Rejected alternatives:** Auto-correcting a detected near-miss content-key server-side instead of asking the repair model to fix it — rejected as exactly the kind of invented-authority shortcut this project's validation layer exists to prevent; naming the mismatch and asking the model to correct it preserves an honest, traceable correction. Silently choosing which of the two colliding `--color-accent` declarations should win (e.g. always preferring the raw color) — rejected as masking a genuine planner-output defect rather than surfacing and preventing it; the planner should never produce a collision in the first place.
- **Consequence:** Confirmed live: the "accent"/"accent" collision was caught instantly and cheaply (failed at the `plan` stage, before any acquire/generate/verify spend) on the run immediately following this fix. One subsequent run reached final whole-site review with all 5 scores at 4 and exactly one blocking finding — the closest this pipeline has gotten to a clean pass, though not yet one. Full end-to-end success (a promoted preview) was not reached this session; remaining live variance is concentrated in whole-site resource-placement rendering (the model rendering decorative placeholder markup instead of the required `LocalImage` component) and generic non-determinism on already-prompted-against rules (e.g. spelled-out `sizes` values), not in the control-flow/validation gaps D-068 and this decision closed. `code generator issues.md` should be updated by whichever session next runs a live confirmation pass.

## D-070 - Enforce live model-cost ceilings before provider transmission

- **Date & Time:** 2026-09-05 16:40 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** An explicitly authorized live pipeline run may contain provider calls whose usage is not persisted when a request is interrupted or returns malformed output. A post-run total cannot protect a caller's ceiling, especially when the run has dependent stages and retries.
- **Decision:** For explicitly capped live validation, wrap the shared structured `ModelClient` in `BudgetedModelClient`. Before every provider request it reserves a conservative prompt charge (including the highest configured ordinary/cache-write prompt rate) plus the maximum completion charge allowed by the remaining ceiling, serializes calls through one lock, and temporarily lowers the provider profile's output cap. On success it settles to finite provider telemetry; on failure, malformed, or missing telemetry it consumes the full reservation. A plain completion is refused because the provider-neutral contract has no safe token override. Durable application caching remains the primary production cost optimization; this wrapper is a run-level safety boundary, not a replacement for the cache.
- **Rejected alternatives:** Checking the total only after the pipeline finishes (too late to protect the cap); allowing each stage to maintain an independent budget (can overspend across sequential stages); assuming failed or canceled calls cost zero (provider usage is not always persisted); and globally lowering the configured model profile (changes normal product behavior and can affect other workers).
- **Consequence:** A bounded live run either reserves a safe request or fails before transmission, while successful short responses return unused reservation to later stages. Unknown usage is intentionally treated conservatively. The September 5 resume validation stopped at Content Architect after `MODEL_EMPTY_OUTPUT`; the missing receipt from an earlier interrupted attempt was not guessed, so later provider calls were not risked.

## D-069 - Use scoped validated-result caching with a long application TTL for the first four agents

- **Date & Time:** 2026-09-05 15:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The first four pipeline agents repeat expensive structured model work when a user retries, refreshes, or regenerates the same approved scope. The stages are sequentially dependent, so any optimization must preserve exact stage boundaries, output validation, and owner isolation. Provider prompt caching is useful for repeated trusted prompt prefixes, but its retention policy is separate from application result retention.
- **Decision:** Add a PostgreSQL-backed `model_call_cache` for Discovery, Content Architect, Visual Design Director, and Build Preparation. Cache only the already-decoded, agent-validated structured output; key it with the cache version, agent/operation, prompt/schema fingerprints, canonical input fingerprint, model profile, and full profile fingerprint. Scope rows to the owning user when available, otherwise to the portfolio session. Use a six-month fixed result TTL, a bounded 15-minute single-flight lease, and a 60-second wait before allowing an uncached fallback. Re-run the same validator on every hit. For the configured Luna OpenAI-compatible profile, send provider prompt-cache hints only when its declared capabilities allow them, with a stable trusted-prefix key/explicit breakpoint and the provider-supported `30m` TTL. Capture token, character, cache, and configured-unit cost telemetry without claiming a universal price. Export each successful stage result under `output/<agent>/<run-id>/`, and show a frontend notice only when a persisted run receipt confirms an actual cache hit.
- **Rejected alternatives:** A global cache without owner/session scope (can cross-contaminate private portfolios); caching prompt text or raw resumes (unnecessary sensitive retention); caching unvalidated fragments (can bypass stage contracts); a browser/local-storage cache (not durable or trustworthy for private state); a sliding TTL (can retain unbounded cold data); and Batch API calls (the stages and adaptive internal calls depend on earlier results and user approvals). Treating the provider prompt-cache TTL as the application result TTL was also rejected: provider prefix reuse and durable result reuse have different correctness and retention requirements.
- **Consequence:** Same-input retries can avoid the model call while preserving the exact validated result, and different prompt/schema/profile/input hashes cannot collide. Six months is intentionally longer than the provider prefix-cache window because structured JSON storage is small relative to model-call cost; cache rows expire as a fixed horizon and are replaced safely on the next request. A cache toast is truthful and non-blocking, and cache identity fingerprints are excluded from local exported metadata.

## D-068 — Close the QUALITY_REVIEW_REJECTED_AFTER_REPAIR and INTEGRATION_POLISH_INCOMPLETE control-flow gaps; extend the resource-catalogue pattern to motion

- **Date & Time:** 2026-09-05 14:30 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** D-067 left the pipeline at its documented frontier: a live run reached final verification for the first time and landed on `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` with one easily-fixable finding (an ARIA target pointing at a paragraph instead of a heading), scores otherwise ≥4. Direct code tracing (confirmed against a second, independent Plan-agent pass) showed this was a pure control-flow gap, not a capability or budget problem: `_attempt_repair`'s post-repair whole-site re-review rejection raises `VerificationFailure` from outside its own bounded retry loop, so it can never consume another round of the existing 6-total/3-per-unit repair budget — the observed case had used only 1 of 6 rounds. Given ~40 prior live-bugfix commits and a pipeline that had just reached its best-ever result, the evidence did not support a rewrite. Live testing this session (after the fix below) surfaced the identical class of gap one stage earlier: the mid-generation whole-site polish loop's owner-scoped repair call (`_review_and_polish`) raised `INTEGRATION_POLISH_INCOMPLETE` and killed the entire run the moment a repair attempt reported `cannot_complete` (repair_source.md's honest escape hatch), even on the very first attempt, even though the outer polish-round loop is already bounded (`max_integration_polish_rounds`, D-067) specifically to give a different round another try. Separately, the single most expensive, most-repeated call in the whole pipeline (whole-site integration review, up to 8x/run, up to ~600,000 chars of context) had zero `request_context` prefix-caching support, unlike 4 of the other 5 call sites. The scaffold's motion system was also found to be completely empty (`motion.css` only a reduced-motion safety net) — every portfolio's animation is invented from scratch by the model in every route_batch/route_compose call, the one remaining unconstrained surface in a pipeline that already uses a deterministic catalogue-and-select pattern for images/fonts/components.
- **Decision:** (1) `_attempt_repair` (`jobs/handlers/code_generator_verification.py`) refactored into `_run_bounded_repair`/`_rereview_after_repair`/`_diagnostics_from_quality_findings` helpers; a rejected post-repair re-review now gets exactly one bounded extra repair+re-review attempt (converting the rejection's blocking findings into `Diagnostic`s and reusing the existing numeric budget) before raising terminally — the re-review itself runs at most twice total, never a third time, regardless of remaining budget. (2) `_review_and_polish`'s owner-scoped repair call now logs and `break`s (skipping that owner for the round) instead of raising on a non-"changes" result, letting the pre-existing bounded polish-round loop keep trying or converge to the pre-existing `INTEGRATION_REVIEW_UNRESOLVED` terminal state. (3) Added `INTEGRATION_REVIEW_KEY_ORDER` (`generation_prompt_builder.py`) and wired `request_context`/`prompt_cache_key` into `integration_review_operation.py`, ordering run-invariant content before the two always-changing scalars (`round`, `source_manifest`) and the large `assembled_source` dict — confirmed live via non-zero `cached_prompt_tokens` in persisted usage. (4) Added `core/motion_pattern_catalogue.py` (3 patterns: reveal-fade-rise, reveal-clip-lines, stagger-group) and an optional `MotionBeatV4.pattern_id` field; when set, `generation_contract.py` instructs route_batch/route_compose to apply a named trusted `SharedSystems.tsx` component exactly instead of hand-authoring new CSS/JS — confirmed live, the planner set `pattern_id` on a real beat on the first live attempt. Also captured raw model `usage` at 3 call sites that previously discarded it (director, redirect-director, final-repair), and added advisory screenshot capture to DOM/runtime verification (zero extra cost, the browser context is already open) since the pipeline had never once captured visual evidence of a generated portfolio.
- **Rejected alternatives:** A ground-up Code Generator rewrite — rejected given ~40 hard-won live-bugfix commits and a pipeline that reached a near-passing final verification on its very last real run; the evidence supported surgical fixes, not a rewrite. Raising `max_repair_rounds_total`/`max_repair_rounds_per_unit` to fix the first gap — rejected, per D-067's own reasoning still standing: the fix works within the existing ceiling and adds its own independent hard cap of exactly one extra attempt, rather than loosening a budget with only one data point. An OpenAI Batch API for the caching work — rejected again per D-040/D-066: still an architectural mismatch for this sequentially-dependent pipeline. A general per-profile cost-tracking/pricing feature — rejected as disproportionate plumbing for a ~$5 total live-verification budget; raw usage capture plus hand-computed cost against the real price sheet is sufficient. Shipping more than 3 motion patterns in this pass — rejected in favor of the 3 lowest-implementation-risk patterns first (no rAF loop or scroll-progress math), deferring count-up/parallax-drift/hover patterns to a follow-up.
- **Consequence:** Two live runs against the eligible pack this session (~$0.06-$0.21 total at published Luna rates) confirmed Fix (3)'s real cache hits and Fix (4)'s live catalogue usage, and surfaced (and got a same-session fix for) the `INTEGRATION_POLISH_INCOMPLETE` gap. Two further attempts were killed by real system memory pressure (not a code defect) before reaching final verification, so Fix (1)'s exact retry firing was not directly witnessed live this session — its bound is proven by 2 new + 1 unchanged regression test instead (`test_attempt_repair_retries_once_after_quality_rejection_then_accepts`, `test_attempt_repair_gives_up_after_one_quality_rejection_retry`). A future session should re-run against the same pack once memory pressure eases and confirm Fix (1) live; `code generator issues.md` should be updated with whatever it finds.

## D-067 — Identify the duplicate path in SOURCE_DUPLICATE_PATH; raise the integration-polish ceiling on live evidence

- **Date & Time:** 2026-09-05 00:55 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** The account behind `OPENAI_API_KEY` was recharged with a corrected key (confirmed live via a cheap, no-content preflight call before any paid generation ran), so Code Generator moved back off ScaleMax onto direct OpenAI. A live run then hit a new, real defect: the v4 duplicate-file-path check in `generation_orchestrator.py` (`_validate_v4_generation_coverage`) raised `SourceValidationError("SOURCE_DUPLICATE_PATH", ...)` without a `file=` value, unlike its sibling checks — the repair model, given a diagnostic naming no file, correctly reported it couldn't make a bounded fix rather than guess (the project's own "honest cannot_complete over guessing" design working as intended, just starved of the one fact it needed). Separately, two independent live runs this session — one on ScaleMax, one on direct OpenAI, same pack — both converged the integration-review polish loop steadily each round (3 blocking findings down to 1, then one lone "bounded motion correction" per the reviewer's own words) but ran out of the `max_integration_polish_rounds` budget (`Field(default=3, ge=1, le=3)`) while still making real progress, not while stuck.
- **Decision:** The duplicate-path check now finds the actual duplicated path(s) and passes the first one as `file=`, with a message naming it explicitly (`generation_orchestrator.py`); new unit test `test_v4_duplicate_path_identifies_the_offending_file`. `max_integration_polish_rounds` raised from `Field(default=3, ge=1, le=3)` to `Field(default=5, ge=1, le=6)` in `core/settings.py`, `config/app.toml` updated to match.
- **Rejected alternatives:** Raising `max_repair_rounds_total`/`max_repair_rounds_per_unit` (the separate final-verification repair budget, D-056/D-058) in the same pass — rejected for now: only one live data point exists showing it too tight (a `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` on a single `missing-section-heading` finding after the polish-ceiling fix let a run reach final verification for the first time), versus two independent cross-provider data points that justified the polish-ceiling raise. A second confirming run is needed before touching an already-separately-reasoned budget. Guessing which file was duplicated instead of computing it — rejected as exactly the kind of invented-authority shortcut the project's validation layer exists to prevent.
- **Consequence:** A live OpenAI run with both fixes reached final verification (build + repair + whole-site re-review) for the first time this session — past the previous universal generate-stage bottleneck entirely — before landing in `needs_attention` on the separate, narrower `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` gate (one real, specific, easily-fixable accessibility finding: a paragraph used where a heading should be). See `code generator issues.md` for the current frontier and next verification target.

## D-066 — Route Code Generator through ScaleMax and restate strict schemas as prompt text

- **Date & Time:** 2026-09-04 20:30 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Direct OpenAI hit `PROVIDER_RATE_LIMIT_ERROR` during route generation even after D-065's serialization. The user supplied a second OpenAI-protocol gateway, ScaleMax, live-verified serving the same `gpt-5.6-luna` model. Switching surfaced a second, unrelated live-only defect: ScaleMax accepts a `strict: true` `json_schema` request (200 OK) but does not reliably enforce it — the director's `CreativeDirectionSetV3` response omitted required fields, mistyped others, and (once the obvious literal-mismatch was fixed) invented an unlisted property (`motion` instead of `motion_vocabulary`). Separately, `prompt_cache_ttl` was configured on every Code Generator profile but was dead code for the OpenAI-compatible adapter (only Anthropic's adapter read it), and the untrusted-input wire payload's `sort_keys=True` serialization interleaved each call's unique keys among the large content that repeats byte-for-byte across a run, defeating any provider-side prefix caching before it could start.
- **Decision:** All 7 Code Generator profiles (`config/models.toml`) move to `provider = "scalemax"` (new dispatch entry in `providers/factory.py`, reusing the existing generic `OpenAICompatibleAdapter` — no new adapter class needed), same model/timeouts/budgets otherwise. `opencode_go.py`'s `_generate_structured_impl` now always restates the exact strict schema as explicit prompt text when `strict_schema=True` (every Code Generator call), in addition to the `response_format` request — redundant-but-harmless for a gateway that already enforces it, a real safety net for one that doesn't. `system.md` gained an explicit "never omit a required field, copy literal enum values exactly" rule. Added an opt-in `request_context={"key_order": [...]}` hook on the previously-unused `request_context` parameter already present on `ModelClient.generate_structured`, so Code Generator's own call sites (director/planner, route batch/compose/integrate/repair, final repair) can place invariant per-run content first and per-call content last in the wire JSON — same JSON shape, no prompt/schema change, zero effect on any other agent, which never sets it. Added an optional `prompt_cache_key` (`codegen:{generation_id}:{role_profile}`), gated by a new `supports_prompt_cache_key` capability flag set only on the 7 Code Generator profiles, mirroring the existing `store` capability-gated pattern.
- **Rejected alternatives:** A bespoke ScaleMax adapter class — rejected because the existing generic OpenAI-protocol adapter already takes `base_url`/`api_key_env` entirely from the profile. Downgrading `structured_output_mode` away from `native_json_schema` for all 7 roles — rejected on 2 data points from one role (director) as too broad a reaction; the narrower prompt-text-restatement fix targets the observed failure directly without discarding a working guarantee elsewhere. An OpenAI-style Batch API for cost — rejected per D-040's reasoning, unchanged: Code Generator's stages are sequentially dependent within one durable job, which does not fit batch's asynchronous turnaround. Reordering the wire payload's actual key insertion order everywhere it's built — rejected as far more invasive than a single opt-in serialization parameter with a safe default.
- **Consequence:** A live run against the supplied test pack got through admission, planning, acquisition, foundation generation, both route batches, route composition, and 3 integration-review/repair polish rounds — the deepest any run reached this session — before landing in `needs_attention` on `INTEGRATION_REVIEW_UNRESOLVED` (a real, specific, mostly-plausible-to-fix review finding set, not a crash or silent failure). See `code generator issues.md` for the full findings table and the new blocker. Real cache-hit savings from the `request_context`/`prompt_cache_key` work were not independently confirmed this session — usage/token data is never persisted to disk in this pipeline, so no post-hoc check was possible; a future session should temporarily log `result.usage` to confirm.

## D-065 — Serialize route-batch provider calls in the bounded generation lane

- **Date & Time:** 2026-09-04 16:05 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Concurrent route-batch generation calls trigger provider 429 rate-limit exhaustion, obscuring whether generation itself is sound.
- **Decision:** Set `route_concurrency = 1` for Code Generator in `config/app.toml`. Keep work-graph parallel-safe, but serialize billable calls and resume from same-run checkpoints.
- **Rejected alternatives:** Raising retries or starting fresh runs (wastes quota without increasing provider capacity); eliminating route batching (bounds context & section ownership); treating 429 as success (publishes incomplete code).
- **Consequence:** One provider call in flight at a time; 429 rate limits are retried once after window reset without re-executing completed foundation/acquisition steps. Readiness status uses shared TTL cache.

## D-064 — Code Generator consumes Markdown briefs through a fenced v5 pipeline

- **Date & Time:** 2026-09-04 16:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** D-062 replaced Build Preparation ZIP packs with two Markdown briefs. Code Generator required admission migration, release fencing, and protection against registry import drift.
- **Decision:** Parse and hash fenced brief JSON indexes at admission. Run active consumer under `code-generator-v5` queue namespace with worker release fencing. Canonicalize distinctive ratios and typography before blueprint validation. Pinned visual references fetch at generation time; optional component registry source is kept in durable materials as reference-only while generated site builds local accessible equivalents.
- **Rejected alternatives:** Restoring ZIP creation/byte embedding (recreates D-062 storage/expiry bloat); allowing v4 workers to claim v5 jobs (mixed rollout schema mismatches); relaxing schemas globally (fails closed on malformed plans; normalizes only deterministic rounding).
- **Consequence:** Markdown briefs directly consumable by standalone and session Code Generator paths. Old workers cannot claim v5 jobs. Pinned images/fonts remain local and browser-addressable; missing optional components fallback safely.

## D-063 — Authenticated product release ends at approved Visual Design Direction

- **Date & Time:** 2026-09-04 05:08 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Normal-user Preact shell exposed incomplete Build Preparation, Code Generator, and Preview stages, while local detached auth mode bypassed real product auth.
- **Decision:** `/app` product journey exposes exactly Discovery, Content Architect, and Visual Design Director, ending at approved direction. Stage transitions require explicit POST calls; no auto-chaining. Product uses `auth.pipeline_mode = "attached"`; developer harnesses use `auth.development_harness_mode = "detached"`.
- **Rejected alternatives:** Displaying later stages as disabled/"coming soon" (advertises incomplete flow); leaving product in detached mode (bypasses auth acceptance); weakening backend authorization on later stages.
- **Consequence:** Verified end-to-end 3-agent creative journey with attached Supabase/Google authentication. Build Preparation and Code Generator remain accessible only via developer routes/APIs until explicitly released.

## D-062 — Build Preparation emits two Markdown briefs instead of a versioned resource pack

- **Date & Time:** 2026-09-03 18:30 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented (Code Generator consumer follow-up completed by D-064)
- **Context:** Build Preparation accumulated ~6,000 lines of byte-downloading, pixel inspection, ZIP packaging, and R2 upload machinery that duplicated downstream Code Generator capabilities.
- **Decision:** Simplify Build Preparation to: (1) Stage 0 scope compilation; (2) search-only discovery research (`resource_research.py` + discovery-only `providers.py`, zero byte downloads); (3) single bounded model call (`compose_visual_brief`) picking candidates by index from researched list or null; (4) deterministic assembly of `content-and-narrative-brief.md` (verbatim Content Architect text) and `visual-and-build-brief.md` (model direction + resource tables), each with one fenced JSON index block. Persist directly on `portfolio_sessions.current_state["build_preparation"]`. Delete packager, materializer, quality, execution, contracts, and checkpoint modules.
- **Rejected alternatives:** Retaining pack-shaped JSON/ZIP without bytes (preserves unnecessary packaging ceremony); prose-only Markdown without structured JSON block (breaks deterministic ID compilation); simultaneous Code Generator rewrite in one pass.
- **Consequence:** Supersedes D-009, D-011, D-013, D-018, D-021, D-025, D-028, D-035, D-051, D-060, D-061. Upstream makes resource decisions; downstream Code Generator acquires bytes at generation time.

## D-059 — Single root .env configuration and pure adapter normalization for Frontend Phase 2

- **Date & Time:** 2026-09-02 22:30 +05:30 — Antigravity (Gemini 2.5 Pro / Google)
- **Status:** decided-implemented
- **Context:** Frontend Phase 2 needed configuration alignment with backend settings, preventing secret leakage and synchronizing cross-tab stage state.
- **Decision:** Use single root `.env` for repository. Frontend build has zero embedded secrets; reads public runtime config dynamically from FastAPI. Client adapters normalize backend responses into pure immutable state models. Synchronize cross-tab stage changes via `BroadcastChannel`.
- **Rejected alternatives:** Maintaining separate frontend `.env`; client-side secret access; manual polling across tabs.
- **Consequence:** Zero client secret exposure; single source of truth for configuration; real-time tab state synchronization.

## D-058 — A cannot-complete repair result consumes one budgeted round, not the whole budget

- **Date & Time:** 2026-09-02 15:30 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** In final verification, an honest `cannot-complete` or host-side content validation error aborting immediately bypassed multi-round repair budgets.
- **Decision:** In `_attempt_repair` (`code_generator_verification.py`), catch `FinalRepairError` and `SourceValidationError` separately. Check `RepairBudget.can_attempt`; while budget allows, retry with `bounded-simplification` strategy hint. Update `projection.repair_rounds` on every attempt. Genuine infrastructure crashes still fail immediately.
- **Rejected alternatives:** Treating any repair exception as immediately terminal; retrying infrastructure/provider network crashes within one job invocation.
- **Consequence:** Honest single-round repair failures do not prematurely terminate runs with remaining budget; receipts accurately track attempted rounds.

## D-057 — Compiler-owned bridge for fixed shadcn semantic slots

- **Date & Time:** 2026-09-02 02:01 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Tailwind registry components use fixed shadcn semantic classes (`--color-<slot>`), which resolve to unbound colors without a theme bridge.
- **Decision:** Add `shadcn_theme_bindings` optional literal-key mapping from shadcn slots to model's exact `colors[].name`. Emit deterministic `--color-<slot>` aliases through checked-in Tailwind v4 `@theme inline` bridge. Provider JSON schema is closed; invalid slots fail local validation with single corrective retry.
- **Rejected alternatives:** Hardcoding palette values (violates D-034); trusting provider cssVars authority; making every slot mandatory.
- **Consequence:** Standard shadcn/Tailwind components adopt portfolio-specific color tokens deterministically before generation.

## D-056 — Final verification repair budgets are per diagnostic group

- **Date & Time:** 2026-09-02 01:15 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Multiple verification gates (source, build, runtime) sharing a single synthetic `final` repair budget caused premature exhaustion on one gate.
- **Decision:** Apply configured per-unit repair ceiling independently to each diagnostic group (source, build, runtime), while enforcing one shared total ceiling and fingerprint recurrence policy. Failed repair must return bounded source change or honest `cannot-complete`.
- **Rejected alternatives:** Raising global per-unit limit (masks repeated failures); removing per-unit ceiling (unbounded looping on single gate).
- **Consequence:** Independent gates utilize separate repair budgets without exceeding run-wide limit; receipt history remains fail-closed.

## D-055 — Code Generator uses dedicated per-role model profiles

- **Date & Time:** 2026-09-02 01:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Standalone Code Generator has 7 distinct roles (director, planner, scout, builder, composer, integrator, repairer), but app routed all through a single profile.
- **Decision:** Route each role in `config/app.toml` through matching dedicated profile IDs in `config/models.toml`. Keep role profiles separate from general pipeline default profile.
- **Rejected alternatives:** Single shared profile for all roles (prevents per-role optimization and granular receipt auditing); hardcoding providers in agent code.
- **Consequence:** Role-specific model tuning, context window adjustments, and provider routing without modifying code.

## D-054 — Shared preview gateway is part of the default Docker stack

- **Date & Time:** 2026-08-27 03:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Standalone preview gateway was profile-gated in Docker Compose, leaving hosted environments unable to serve verified preview objects.
- **Decision:** Include `preview-gateway` in default Docker Compose topology alongside API and worker. Probe via `http://preview-gateway:4174/health/live`. Previews remain immutable S3-compatible objects; local dev uses filesystem storage.
- **Rejected alternatives:** Leaving gateway profile-gated; creating dedicated container per portfolio preview; merging isolated dev harness into main production stack.
- **Consequence:** Consistent containerized preview boundary across local and hosted environments.

## D-053 — Extend temporary detached auth to the Code Generator standalone dev harness

- **Date & Time:** 2026-08-25 21:10 +05:30 — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Standalone Code Generator harness (`code_generator_development.py`) was admin-gated, preventing local iteration when `pipeline_mode = "detached"`.
- **Decision:** Mirror D-052 router-split pattern: mount `detached_router` (no auth dependency) when `pipeline_mode == "detached"`, and `router` (`require_admin`) in attached modes. Keep session-bound production routes (`code_generator.py`) fully protected.
- **Rejected alternatives:** Removing auth from production Code Generator routes; inventing an ad-hoc bypass mechanism.
- **Consequence:** Standalone development harness operates login-free in detached mode; production routes retain full Phase 3/4 auth and entitlement enforcement.

## D-052 — Extend temporary detached auth through the Build Preparation fixture

- **Date & Time:** 2026-08-25 20:09 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Build Preparation fixture required administrator API token and redirected to sign-in even when main pipeline was detached.
- **Decision:** In `auth.pipeline_mode = "detached"`, Build Preparation fixture and progress APIs accept anonymous requests; browser skips Supabase bootstrap. Attached, Docker, and production modes retain strict admin authentication.
- **Rejected alternatives:** Disabling auth globally; client-only bypass without API alignment.
- **Consequence:** Supersedes D-049. Native developer fixture opens directly without login friction; protected production environments remain fail-closed.

## D-050 — Detached pipeline model selection and privacy-free preflight

- **Date & Time:** 2026-08-25 11:54 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Detached development required switching model profiles for testing without leaking credential configuration or sending portfolio context during preflight.
- **Decision:** Expose detached-only APIs for allowlisted profile labels and fixed-schema, no-context preflight. Selection persists in Discovery and is inherited by downstream stages. Attached modes fail closed.
- **Rejected alternatives:** Exposing provider endpoints/credentials to frontend; preflighting with real user documents; allowing stages to diverge profiles mid-run.
- **Consequence:** Privacy-safe preflight; persistent run-level model selection in detached development.

## D-048 — Make Google registration open by deployment configuration

- **Date & Time:** 2026-08-24 18:30 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Initial 3-account email allowlist blocked valid Google OAuth onboarding and conflicted with Google's OAuth testing limits.
- **Decision:** Introduce `auth.admission_mode`: `open` admits any verified Google account up to database capacity of 15 normal users; `allowlist` restricts admission via `ORYXENAI_ALLOWED_USER_EMAILS`. Bootstrap admins bypass normal-user capacity.
- **Rejected alternatives:** Removing server capacity gate; client-side access toggles; application-level passwords/OTP.
- **Consequence:** Self-serve onboarding for early access up to 15-user quota; strict server-side capacity enforcement.

## D-047 — Complete Phase 4 administrator lifecycle with resumable local authority

- **Date & Time:** 2026-08-24 14:40 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Administrator actions (user deletion, portfolio reset, audit logging) required database-authoritative safety across external Supabase and preview storage systems.
- **Decision:** Add linear Alembic migration for lifecycle state, admin operations audit, and identity tombstones. Require active onboarded admin, target confirmation, bounded idempotency keys, and short DB transactions. Fence queued work; delete only exact session-scoped storage/local paths; call Supabase Admin API for provider user suspension/deletion; require explicit audited readmission. Entitlement resets permitted only after verified project deletion.
- **Rejected alternatives:** Browser-only admin checks; provider metadata roles; broad storage prefix deletion; automatic deleted-user readmission; treating failed provider calls as completed deletion.
- **Consequence:** Safe, resumable, audited admin lifecycle operations; deleted users cannot re-enter via JIT admission.

## D-046 — Enforce Phase 3 entitlement and worker safety in PostgreSQL-backed durable state

- **Date & Time:** 2026-08-24 04:00 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Normal users required enforcement of 1 session, 1 variant, and 1 promoted portfolio success, while background jobs required immunity to late ownership changes.
- **Decision:** Create `portfolio_entitlements` row per normal user in migration `0016_auth_entitlements_worker_fencing`. Persist local session/owner/actor snapshots on jobs and runs. Worker reauthorizes snapshots immediately before claiming work, enqueuing successors, and finalizing preview promotion. Enforce single global PostgreSQL `model-generation` concurrency lane via partial unique index. Admins are entitlement-unlimited.
- **Rejected alternatives:** Client-side quota; in-process worker mutex; trusting job payloads; consuming success entitlement before verified promotion.
- **Consequence:** Multi-worker safe entitlement enforcement; server-idempotent Code Generator execution; changed owner/entitlement fences late jobs fail-closed.

## D-045 — Execute Phase 2 as session ownership and API authorization retrofit

- **Date & Time:** 2026-08-24 02:00 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Pre-existing portfolio sessions were globally ID-addressable and lacked user ownership boundaries.
- **Decision:** Add `portfolio_sessions.owner_user_id` with `ON DELETE RESTRICT` and `legacy_quarantined` state. Quarantine all pre-Phase-2 sessions. FastAPI dependencies and `PortfolioAccess` enforce ownership: normal users see only owned non-legacy sessions; admins can access owned and legacy sessions. Protect all nested stage routes.
- **Rejected alternatives:** Assigning legacy sessions to first login; client-asserted user IDs; in-memory Python filtering; browser Data API policies.
- **Consequence:** Strict multi-tenant session isolation; legacy test sessions quarantined to admin view.

## D-044 — Execute authentication Phase 1 without advancing authorization phases

- **Date & Time:** 2026-08-23 23:45 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Required an independently testable identity layer without prematurely mutating portfolio ownership or worker authorization.
- **Decision:** Phase 1 delivers: Supabase Google-only session restoration, server-side asymmetric JWT/JWKS verification, JIT `app_users` admission with 15-user capacity gate, 2 bootstrap admins, username onboarding, and `GET /api/v1/me`. Portfolio routes left unchanged pending Phase 2.
- **Rejected alternatives:** Combining identity, ownership, and entitlements into one mega-migration; client metadata authorization.
- **Consequence:** Isolated identity foundation; clean separation between authentication and downstream authorization phases.

## D-043 — Supabase Google identity with database-authoritative authorization

- **Date & Time:** 2026-08-23 20:48 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Needed managed authentication for small allowlisted deployment without managing passwords, custom OAuth tokens, or redundant identity services.
- **Decision:** Use Supabase Auth solely as IDP with Google sign-in. FastAPI verifies asymmetric Supabase JWTs. PostgreSQL is authoritative for user records, usernames, roles, 15-account capacity, resource ownership, and entitlement state. Roles/authorization never derived from client metadata or query parameters.
- **Rejected alternatives:** Clerk (adds redundant service); public registration without capacity gate; custom password/OTP auth; frontend-only quota.
- **Consequence:** Authoritative local database authorization backing external Google identity; fail-closed token validation.

## D-042 — Stable retry and explicit new-variant semantics

- **Date & Time:** 2026-08-23 00:00 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Retries on infrastructure failures must not burn external model calls or overwrite verified previews, while intentional regenerations must produce distinct creative work.
- **Decision:** Automatic retries and POST `/retry` reuse the run's immutable variant receipt, fingerprint, accepted checkpoints, and preview. Explicit POST `/regenerate` creates a new run/variant, checks fingerprint divergence from recent variants, and fails closed if output is too similar.
- **Rejected alternatives:** Creating new design variant on every retry; in-place mutation of accepted variants; deleting active preview before replacement is verified.
- **Consequence:** Idempotent, safe retries; controlled, verifiable design diversity on intentional regeneration.

## D-041 — Code Generator V4 provider-compatible contracts and preview truth

- **Date & Time:** 2026-08-21 22:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** V3 generation allowed schema drift between development and session paths, marker-only visual assertions, and loose preview gateway CSP.
- **Decision:** Introduce mapping-free v4 typed contracts (creative, blueprint, search-intent, source-envelope, quality-receipt, typed-token). Compile semantic route ownership deterministically; execute whole-site review across dev and session runs; retain verified candidates as `preview_pending` on publication failure; enforce strict iframe embed-origin CSP on preview gateway.
- **Rejected alternatives:** Replacing v3 in place without backward-compatibility; marker text as visual proof; wildcard iframe CSP.
- **Consequence:** Fail-closed validation on missing executable evidence; precise provider diagnostic receipts; resilient preview preservation.

## D-040 — Configuration-driven Anthropic default and model routing

- **Date & Time:** 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Needed unified model switching across engines without scattering provider conditionals in agent code.
- **Decision:** Route all engines through shared `ModelRouter` and provider-neutral `ModelClient`. Committed profile uses Anthropic Claude Sonnet 5 with `ANTHROPIC_API_KEY`, adaptive thinking, and schema declarations. Configuration lives in `config/models.toml`; API exposes non-secret metadata only.
- **Rejected alternatives:** Hardcoding provider branches in agents; client-driven provider overrides; silent fallback to mocks for live jobs.
- **Consequence:** Changing model or provider is a TOML configuration change; live operations fail closed when credentials or capabilities are missing.

## D-039 — Backend-only Docker and shared hosted portfolio previews

- **Date & Time:** 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Ephemeral free-tier container hosting makes per-portfolio containers expensive and fragile. Static React/Vite portfolios need lightweight hosting.
- **Decision:** Docker packages only OryxenAI API, background worker, migration environment, browser verifier, and shared preview gateway. Generated portfolios remain portable source trees + `dist/`. Hosted previews use immutable S3-compatible objects behind shared gateway; local dev uses filesystem.
- **Rejected alternatives:** Spawning a container or deployment per portfolio; serving preview HTML directly from container filesystem; running generated app as dev server.
- **Consequence:** Inspectable, portable static outputs; shared preview origin eliminates per-site infrastructure costs.

## D-038 — Promotion requires content-addressed artifact reuse and terminal diagnostics

- **Date & Time:** 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Provider schema errors, invalid plan layouts, and browser verification crashes were causing infinite retries or false-positive promotions.
- **Decision:** Provider capability negotiation at shared boundary; 1 bounded correction attempt for invalid planner output; route workspaces are source-only with shared dependencies; browser verification runs in isolated directories with tokens; preview promotion allowed only when source, build, and DOM runtime checks agree.
- **Rejected alternatives:** Hardcoded portfolio repair heuristics; unbounded model retries; reinstalling node_modules per route wave.
- **Consequence:** Deterministic, bounded repair cycles; terminal failures persist diagnostic reports without silent retry looping.

## D-037 — Provider wire contracts and no-context Code Generator admission

- **Date & Time:** 2026-08-21 00:30 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Model providers reject typed schema mappings before planning, while readiness checks could claim success without exercising the live provider.
- **Decision:** Declare wire capabilities in config. Adapter emits native JSON Schema for supported subset, using schema prompting + local validation for typed mappings. Require no-context provider preflight before live runs; retry structurally invalid planner responses once with bounded feedback.
- **Rejected alternatives:** Hardcoded per-portfolio schemas; silent provider fallback; treating API ping as model readiness.
- **Consequence:** Provider incompatibilities caught before sending portfolio data; actionable admission errors in UI before durable jobs launch.

## D-036 — Enforce generated source and runtime contracts without visual evidence

- **Date & Time:** 2026-08-20 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Generating visual layout requires concrete source and DOM invariants rather than unverified LLM text claims.
- **Decision:** Deterministic TypeScript source audit and exact DOM/runtime checks (AST syntax, imports, exports, non-empty text, interactive element contrast/reachability). Multi-viewport headless Chromium verification before promotion.
- **Rejected alternatives:** Trusting LLM claims of layout validity; relying solely on `vite build` without runtime DOM verification.
- **Consequence:** Every promoted portfolio is guaranteed syntactically valid, type-clean, and geometrically renderable across desktop and mobile viewports.

## D-034 — Design-neutral Code Generator V3 with compiler-owned behavior

- **Date & Time:** 2026-08-20 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Free-form HTML generation produced visual drift, broken responsiveness, and inconsistent styling.
- **Decision:** Replace free-form generation with typed `ExperienceBlueprint`. Compiler owns color token mappings, Tailwind layout classes, and semantic slot bindings. LLM provides design intent and section semantics, not raw markup.
- **Rejected alternatives:** Allowing model to emit arbitrary CSS/inline styles; template-only portfolio stamping.
- **Consequence:** Architectural consistency across generated portfolios while maintaining aesthetic distinctiveness.

## D-033 — Fenced Code Generator stage attempts and immutable workflow artifacts

- **Date & Time:** 2026-08-20 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Stale workers or retried jobs could overwrite later stage progress on long generation runs.
- **Decision:** Persist immutable stage receipts and unique attempt tokens for every generation step. CAS revision checks reject late or stale worker writes.
- **Rejected alternatives:** In-memory worker locking; unconditional stage state overwrites.
- **Consequence:** Zombie or delayed background workers fail closed without corrupting active generation runs.

## D-032 — Session-bound Code Generator with compiled visual execution

- **Date & Time:** 2026-08-19 12:34 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Code Generator required binding to persistent portfolio session state rather than running only as a detached harness.
- **Decision:** Production Code Generator runs as durable session job (`code_generator.build`), consuming approved handoff briefs. Persist progressive state directly on session JSONB.
- **Rejected alternatives:** Decoupling code generation entirely from portfolio database sessions; running code generation inside HTTP request lifecycle.
- **Consequence:** Resumable, session-tracked portfolio generation with database-authoritative run status.

## D-031 — Shared local Pexels/Pixabay image retrieval

- **Date & Time:** 2026-08-18 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Generated sites need real photographic assets without allowing unvetted web scraping or runtime hotlinking.
- **Decision:** Shared image retrieval service queries Pexels/Pixabay APIs, validates licensing and aspect ratios, and stores local references. Downstream generator materializes bytes into local assets.
- **Rejected alternatives:** Hotlinking external image URLs; model-hallucinated image URLs; AI image generation for realistic evidence.
- **Consequence:** License-compliant, local browser-addressable image assets in every generated portfolio.

## D-030 — Priority-based dynamic component retrieval

- **Date & Time:** 2026-08-18 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Rich interactive components required selection without bundling large monolithic component libraries.
- **Decision:** Query component registries by semantic tags based on approved design requirements. Selected components provide local recipes or fallback to accessible Tailwind primitives.
- **Rejected alternatives:** Installing all components upfront; bundling huge UI libraries into every portfolio.
- **Consequence:** Lean generated bundles containing only the components strictly required by the design.

## D-029 — Cache-free live component retrieval

- **Date & Time:** 2026-08-18 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Stale component cache caused version mismatches and broken imports during generation.
- **Decision:** Component discovery queries upstream registries per run; validate retrieved source against schema before admittance.
- **Rejected alternatives:** Storing persistent binary component cache across generation runs.
- **Consequence:** Clean component admittance without cache invalidation bugs.

## D-027 — Verified major tasks end in task-scoped local commits

- **Date & Time:** 2026-08-17 15:46 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Multi-agent collaboration across different AI tools and branches requires clean, verifiable git boundaries.
- **Decision:** Completed, verified units of work that qualify for `CHANGES.md` must end with a task-scoped local Git commit. Stage only task-owned files; never use `git add .` in dirty worktrees.
- **Rejected alternatives:** Leaving code uncommitted for user to commit; bulk staging entire repository.
- **Consequence:** Repository invariant: atomic, traceable, task-scoped commits across all AI tools.

## D-026 — Code Generator core is the sole standalone implementation namespace

- **Date & Time:** 2026-08-17 14:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Code Generator code was split between standalone development prototypes and production session code.
- **Decision:** Consolidate Code Generator logic under `src/oryxenai/agents/code_generator/core/`. Standalone harness and production service share identical core compilation, planning, and verification modules.
- **Rejected alternatives:** Maintaining duplicate generator logic for standalone harness vs production session.
- **Consequence:** Single implementation path; fixes in standalone harness automatically benefit production generation.

## D-024 — Export complete verified portfolios with receipt-bound metadata

- **Date & Time:** 2026-08-17 12:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Users require clean, self-contained portfolio exports ready for independent deployment.
- **Decision:** Export builds clean ZIP containing verified source tree, `dist/`, asset references, and export manifest with audit receipts.
- **Rejected alternatives:** Exporting raw unbuilt source; omitting verification receipts.
- **Consequence:** Standalone deployable portfolio artifacts with full provenance metadata.

## D-023 — Harden generated filesystem transitions on Windows

- **Date & Time:** 2026-08-17 11:10 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Windows file locks (antivirus, indexer, Vite) caused transient `PermissionError` during atomic directory replacement.
- **Decision:** Route directory swaps, tree deletion, and atomic writes through `fs_safe` layer with extended paths (`\\?\`), exponential backoff retry, and explicit error handling.
- **Rejected alternatives:** Ad-hoc try/except per file call; ignoring deletion failures; disabling directory replacement.
- **Consequence:** Atomic checkpoints and directory promotion reliably succeed on Windows platforms.

## D-022 — Skip acquisition for execution-contract-resolved resource slots

- **Date & Time:** 2026-08-17 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Re-fetching already resolved resources wasted bandwidth and introduced network failure points.
- **Decision:** Acquisition engine checks execution contract; skips network retrieval for pre-resolved slots, executing fetches only for gap slots.
- **Rejected alternatives:** Unconditionally refetching all assets on every step.
- **Consequence:** Minimal external API calls; fast, deterministic asset compilation.

## D-020 — Approved external links are content, not runtime navigation

- **Date & Time:** 2026-08-15 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** External portfolio links (GitHub, LinkedIn, live demos) were colliding with SPA router navigation.
- **Decision:** External URLs are treated strictly as content data, rendering standard HTML `<a>` anchors with `target="_blank"` and `rel="noopener noreferrer"`. Router handles only internal route IDs.
- **Rejected alternatives:** Routing external URLs through SPA router; converting external links to synthetic pages.
- **Consequence:** Clean separation between internal SPA routes and external portfolio references.

## D-019 — Normalize strict-schema generation payloads by mode tag

- **Date & Time:** 2026-08-15 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Models emitting JSON objects in structured output mode require discriminated envelope schemas.
- **Decision:** Tag generation payloads with an explicit `mode` enum (`foundation`, `route`, `review`, `repair`). Validate envelopes strictly against mode-specific schemas.
- **Rejected alternatives:** Unvalidated loose JSON dicts; single monolithic schema for all generation phases.
- **Consequence:** Type-safe model output parsing with early structural rejection of malformed outputs.

## D-017 — Approve a complete safe public scope, then direct that exact scope

- **Date & Time:** 2026-08-14 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Downstream agents inventing new routes or sections caused scope creep and inconsistent portfolios.
- **Decision:** Content Architect defines and user approves complete public scope (routes, sections, navigation). Visual Design Director and Code Generator must execute that exact scope without inventing new pages or omitting approved ones.
- **Rejected alternatives:** Allowing later agents to add surprise pages or drop approved sections.
- **Consequence:** Upstream scope approval is binding on all downstream generation stages.

## D-016 — Content Architect approval requires at least one publishable route

- **Date & Time:** 2026-08-13 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Approving an empty or draft-only content structure caused downstream build failures.
- **Decision:** Enforce validation rule: approved content snapshot must contain at least one valid, publishable route with content.
- **Rejected alternatives:** Allowing empty approved state; deferring route existence checks to Code Generator.
- **Consequence:** Downstream agents always receive non-empty, actionable route scope.

## D-015 — Code Generator uses progressive text-only generation with mediated resource acquisition

- **Date & Time:** 2026-08-13 14:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Monolithic generation of full site code in a single prompt hit context limits, hallucinated dependencies, and suffered syntax corruption.
- **Decision:** Deconstruct generation into progressive, text-only sequential stages: planning -> foundation & design system -> route waves -> cross-route review -> bounded repair. Resource acquisition (images, fonts, components) is mediated by deterministic code, never LLM tool loops.
- **Rejected alternatives:** Single-prompt full codebase generation; allowing LLM direct web access.
- **Consequence:** Supersedes D-014. Predictable token consumption, deterministic file boundaries, and granular error isolation.

## D-008 — Visual Design Director mirrors Content Architect architecture

- **Date & Time:** 2026-08-09 18:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Third pipeline stage needed an architecture consistent with Content Architect without conversational chat overhead.
- **Decision:** Mirror Content Architect's pattern: explicit start via POST endpoint, single durable job (`visual_design_director.build`), 1-3 sequential model calls (`establish_visual_language`, optional `direct_page_experience`, optional `integrate_site_experience`), deterministic tag-overlap lookup over checked-in resource catalogue, JSONB persistence on session state, hash-checked approval.
- **Rejected alternatives:** Interactive chat UI for Visual Design Director; auto-chaining from Content Architect approval; agentic tool-calling loop for catalogue search.
- **Consequence:** Supersedes D-006. Architectural uniformity across pipeline stages; predictable bounded execution.

## D-007 — Restructure AI-agent context files around canonical AGENTS.md

- **Date & Time:** 2026-08-08 20:00 UTC — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Multiple AI tools (Codex, Claude Code, Antigravity, Cursor) active in the repository require consistent, authoritative context without duplicate drift.
- **Decision:** Establish `AGENTS.md` as canonical root context file for all tools. `CLAUDE.md`, `.cursorrules`, and tool configurations reference `AGENTS.md`. Maintain config-driven policy: never hardcode model names, API keys, or live status in prose.
- **Rejected alternatives:** Maintaining separate, divergent context files for each AI assistant.
- **Consequence:** Unified cross-tool protocol; zero discrepancy between AI coding assistants.

## D-005 — Jinja2 + vanilla JS testing harness instead of framework frontend

- **Date & Time:** 2026-08-08 00:00 UTC — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Needed lightweight UI to test Discovery and stage APIs before committing to a heavy frontend architecture.
- **Decision:** Built initial test UI with Jinja2 templates, vanilla JS, and CSS served directly by FastAPI.
- **Rejected alternatives:** Premature Next.js or React setup during core engine stabilization.
- **Consequence:** Rapid iteration on engine APIs without frontend build toolchain friction.

## D-004 — Kept dormant discovery_opencode_go profile in config/models.toml

- **Date & Time:** 2026-08-07 20:30 UTC — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** OpenCode Go provider was rate-limited, but preserving the configuration for future fallback was desirable.
- **Decision:** Retain `discovery_opencode_go` profile in `config/models.toml` while routing active profiles through OpenAI/Anthropic.
- **Rejected alternatives:** Deleting the provider configuration entirely.
- **Consequence:** Fast provider re-enabling via TOML profile reassignment without code changes.

## D-003 — Switched Discovery/Content Architect to OpenAI API directly

- **Date & Time:** 2026-08-07 20:10 UTC — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** OpenCode Go rate limit quota exhausted during early development.
- **Decision:** Pointed active engine profiles directly to OpenAI API. Introduced `ModelCapabilities` layer to abstract provider differences (e.g. `uses_max_completion_tokens`).
- **Rejected alternatives:** Waiting for provider quota reset; hardcoding provider checks in agent code.
- **Consequence:** Provider neutrality established; generic capabilities abstraction handles wire differences.

## D-002 — v1 Discovery over-engineering, then v2 simplification

- **Date & Time:** 2026-08-07 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Initial Discovery had dedicated document tables, repair loops, 20-file few-shot libraries, and fact graph validation.
- **Decision:** Simplified to session JSONB storage, inline contrastive prompt examples, and envelope-only validation. Markdown brief content is free-text.
- **Rejected alternatives:** Preserving complex multi-table validation graph and schema validation on free-text briefs.
- **Consequence:** Standard established: envelope validation + prompt-carried examples over heavy framework machinery.

## D-001 — Explicit Python agents over an agent framework

- **Date & Time:** 2026-08-06 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Required agent architecture before tool-calling and routing requirements were fully established.
- **Decision:** Plain Python protocols (`Agent`, `ModelClient`) and Pydantic schemas without external frameworks.
- **Rejected alternatives:** LangChain, LangGraph, CrewAI, AutoGen.
- **Consequence:** High testability, zero framework lock-in, explicit model boundaries, full architectural control.

---

## Compacted & Superseded History

- **D-107** — 2026-09-21 17:39 +05:30 — Claude Code (Sonnet 5) — GitHub Actions CI stays verification-only, Azure deployment stays manual SSH (superseded by D-110 gated self-hosted-runner CD)
- **D-061** — 2026-09-03 11:35 +05:30 — Claude Code (Sonnet 5) — Build Preparation 100-year pack TTL (superseded by D-062 Markdown briefs)
- **D-060** — 2026-09-03 01:45 +05:30 — Claude Code (Sonnet 5) — Deferred materialization of pack bytes (superseded by D-062 Markdown briefs)
- **D-051** — 2026-08-25 11:54 +05:30 — Codex (GPT-5) — Source-bound Build Preparation JSONB checkpoints (superseded by D-062 Markdown briefs)
- **D-049** — 2026-08-25 16:30 +05:30 — Codex (GPT-5) — Temporary detached authentication in main pipeline (superseded by D-052)
- **D-035** — 2026-08-20 00:00 +05:30 — Codex (GPT-5) — Build Preparation v4 delegated acquisition (superseded by D-062 Markdown briefs)
- **D-028** — 2026-08-17 22:00 +05:30 — Codex (GPT-5) — Real provider material mandatory for visual handoff slots (superseded by D-062 Markdown briefs)
- **D-025** — 2026-08-17 14:00 +05:30 — Codex (GPT-5) — Required visual handoff uses executable local bindings (superseded by D-062 Markdown briefs)
- **D-021** — 2026-08-16 00:00 +05:30 — Codex (GPT-5) — Keep one canonical storage-key route owner (superseded by D-062 Markdown briefs)
- **D-018** — 2026-08-15 00:00 +05:30 — Codex (GPT-5) — Pack-v3 makes known resource decisions executable before Code Generator (superseded by D-062 Markdown briefs)
- **D-014** — 2026-08-13 10:36 +05:30 — Codex (GPT-5) — Code Generator v1 bounded generation, verification, repair, preview promotion (superseded by D-015)
- **D-013** — 2026-08-12 21:00 +05:30 — Codex (GPT-5) — Repair Build Preparation pack defects & issue pack v2 (superseded by D-062 Markdown briefs)
- **D-012** — 2026-08-12 20:45 +05:30 — Codex (GPT-5) — Freeze Build Preparation v1 and validate through Code Generator (superseded by D-013)
- **D-011** — 2026-08-11 00:00 +05:30 — Codex (GPT-5) — Rebuild Build Preparation as real agent from zero (superseded by D-062 Markdown briefs)
- **D-010** — 2026-08-10 17:51 +05:30 — Codex (GPT-5) — Portfolio Production Compiler pre-code boundary (superseded by D-011)
- **D-009** — 2026-08-10 00:00 +05:30 — Codex (GPT-5) — Deployment-independent temporary Build Preparation packs (superseded by D-062 Markdown briefs)
- **D-006** — 2026-08-08 15:30 UTC — Claude Code (Sonnet 5) — Visual Design Director & Code Generator deferred (superseded by D-008)

---

## Summary (as of last update — 2026-09-18)

- Total decisions logged: 99 (highest entry ID D-099)
- Compacted & superseded decisions: 16 (see `## Compacted & Superseded History` below)
- Last updated: 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5)
