# OryxenAI — Architecture Decision Records

Compact ledger of active architectural decisions. For historical entries prior to D-115, consult Git history.

---

## D-137 — Light PDF engine for the Render Free image

- **Date & Time:** 2026-10-05 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** Docling and PyTorch load and build heavily for a 512 MB service. A three-page scanned PDF exceeded the 120-second extraction limit in a 512 MiB test container at 0.5 CPU while reaching about 440 MiB; Render Free has 0.1 CPU.
- **Decision:** Keep Docling as the local full engine and a `pdf-full` optional dependency. The Free overlay selects PDFium text extraction with `light_ocr = false`. Scanned PDFs receive a clear instruction to export a text-based PDF or paste text. Both engines share the upload, encryption, page, time, and character limits. The Docker image defaults to the light path and does not download Docling or Chromium assets at runtime. Keep RapidOCR available for a larger-plan light OCR profile.
- **Trade-off:** Layout and table fidelity is simpler on the Free host, and scanned PDFs cannot be read there. Browser verification stays off in that overlay while Studio's owner preview remains available.

## D-136 — Render release after a green staging commit

- **Date & Time:** 2026-10-05 — Codex (OpenAI)
- **Status:** implemented-locally; external setup pending
- **Context:** The owner wants push-driven CI/CD without PR review, while routine pushes must not change the live domain. The existing `deployment` ruleset requires a PR and its CI deploy job targets the retired Azure VM.
- **Decision:** `staging` runs CI only. An exact SHA that passes there can be fast-forward pushed to `deployment`; CI runs again and Render deploys only after checks pass. Remove the ruleset's PR requirement while retaining the required quality check, deletion protection, and force-push protection. Use one Render Free Docker web service with Supabase Auth and PostgreSQL, startup migrations, and a combined API/worker process. Keep Azure files for rollback until live acceptance.
- **Trade-off:** A release still requires a deliberate branch push. Render Free may sleep or exhaust its included hours; the durable queue resumes when the service wakes.

## D-135 — Private workspace pages and honest first-build presentation

- **Date & Author:** 2026-10-04 18:55 +05:30 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** Primary actions drifted across screens and vanished below long review content; visual choices lacked distinction; the first Studio build lacked progress feedback.
- **Decision:** Unified viewport action dock for primary stage CTAs. Added authenticated Home and Guide views (`/app?view=...`) with safe post-auth redirect. Rendered distinct equal-sized card previews for all 4 themes. Displayed an illustrative code build animation for >=30s (yielding to verified preview or failure by 40s). Product pages are noindexed.
- **Rejected alternatives:** Auto-advancing stages on navigation; simulated backend logs or fake success claims; advertising unbuilt publishing/download/hosting features.
- **Consequence:** Clean frontend navigation and honest presentation without modifying backend durable jobs, approval boundaries, or sealed versions.

## D-134 — Canonical Content Architect evidence paths and failure-only diagnostics

- **Date & Author:** 2026-10-04 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** Content Architect runs failed readiness validation because model outputs prefixed coverage paths with `page_content.`. Retries replayed cached stage results. Failure screens lacked copyable diagnostic reports.
- **Decision:** Canonicalize/strip `page_content.` prefix from claim and coverage field paths at the CA boundary (for both fresh and cached responses). User retries explicitly bypass structured result caching. Persist bounded, content-free issue locations in failure envelopes. Added a single "Copy diagnostics" action on failure screens.
- **Rejected alternatives:** Loosening path validation for arbitrary prefixes; exposing raw model output or portfolio copy in diagnostics; clearing owner-wide cache on reset.
- **Consequence:** Pre-existing failed responses validate cleanly. Manual retries fetch fresh model outputs. Diagnostics are safe, time-stamped, and user-initiated.

## D-133 — Host-rendered page body for themes with an exact renderer; labelled assumptions for sparse input

- **Date & Author:** 2026-10-04 — Claude Code (Anthropic)
- **Status:** implemented-locally
- **Context:** LLMs repeatedly failed closed-world validation trying to reproduce body markup that is a pure function of approved content (Cobalt Atlas v2). Thin Discovery input left Atlas sections empty.
- **Decision:** Theme contracts implementing `render_body` (`HostRenderedContract`) build deterministically on the host (no LLM call), followed by normal validation, sealing, and browser verification. All 4 registered themes now render on host. For sparse Atlas input, Content Architect adds `kind="sample"` rows visibly tagged in templates and flagged as `Assumed:` in review warnings.
- **Rejected alternatives:** LLM generation with host fallback/retry (violates no-auto-repair invariant in AGENTS.md); unlabelled invented details; separate assumption envelope fields.
- **Consequence:** Page builds take milliseconds with zero copy mismatch; chat edits rebuild deterministically. Assumed data is explicitly labelled.

## D-132 — Theme exemplars use `{path}` placeholders, never sample copy

- **Date & Author:** 2026-10-04 — Claude Code (Anthropic)
- **Status:** implemented-locally
- **Context:** Cobalt Atlas v2 exemplar contained sample copy that the LLM reproduced into `aria-label` or `data-title`, violating closed-world validation. Exemplars also lacked coverage for case-id gaps.
- **Decision:** Render exemplars via `placeholderize(sample)` (`oryxenai.themes.placeholders`): every string becomes `{field.path}`, covering all optional branches and gaps. Unit tests validate exemplars against placeholders. Composed-value validator reports expected vs found.
- **Rejected alternatives:** Model repair/retry loops or relaxing closed-world validation.
- **Consequence:** All scripted theme exemplars must use placeholder tokens. Pinned theme assets remain untouched.

## D-131 — Fourth scripted Atlas theme and grounded sparse work

- **Date & Author:** 2026-10-04 12:25 +05:30 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** Added a 4th pre-built design (`style.css` + `theme.js`) with Home, About, and optional case studies. Users often lack project details or photographs.
- **Decision:** Packaged as immutable `cobalt-atlas/v2` with local fonts, host script inclusion, strict markup contract, bundle hashes, and sandboxed preview (`sandbox allow-scripts`, no `allow-same-origin`). Discovery offers 4th visual choice + work question. Content Architect fills Atlas supplement; sparse work renders abstract CSS art, designed invitation, and initials placeholder. Studio chat supports Atlas edits.
- **Rejected alternatives:** User-specific JS/CSS; model-written scripts; invented achievements; ungrounded photos before asset workspace exists.
- **Consequence:** Supersedes D-128 research proposal. Preserves immutable v1 themes.

## D-130 — Resilient Supabase authentication provider reads

- **Date & Author:** 2026-10-04 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** Long-running API threw `AUTH_PROVIDER_UNAVAILABLE` on transient Supabase transport errors; failed JWKS refresh discarded cached keys.
- **Decision:** Recreate bounded auth HTTP client on transport errors; retry idempotent GETs once; keep admin mutations single-shot. Cache last known JWKS up to 3,600s across outages; 30s failed-refresh backoff; rate-limit unknown-key lookups. Browser retries `/api/v1/me` twice before offering manual retry.
- **Trade-off:** Revoked keys may be accepted for up to 1 hr during total Supabase downtime; token signature, issuer, and expiry checks remain enforced.
- **Consequence:** Browser sessions survive transient provider downtime without configuration or infrastructure changes.

## D-129 — Discovery palette selects an immutable Studio theme

- **Date & Author:** 2026-10-03 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** Needed user visual preference during Discovery to select between pre-built portfolio designs.
- **Decision:** Added required palette question at end of Discovery interview. Swatches map deterministically to Editorial Forest Motion, Cobalt Atlas, or Obsidian Signal. Theme ID is pinned to session state, approval hash, and generator runs. Each theme retains independent CSS, markup contract, and manifest.
- **Rejected alternatives:** Model-selected themes; freeform mood parsing; runtime CSS mutation.
- **Consequence:** Theme selection is deterministic and immutable across build, edits, and restore.

## D-128 — Proposed interactive Studio theme using pre-built JavaScript

- **Date & Author:** 2026-10-03 — Codex (OpenAI)
- **Status:** proposed-research-only (superseded by D-131)
- **Context:** Explored pairing model-generated `body_html` with pre-built CSS/JS scripts while preserving strict preview sandboxing.
- **Decision:** Outlined host-injected `theme.js`, CSP sandbox flags, integrity checks, and Chromium behavioral tests in `docs/research/studio-interactive-theme-architecture.md`.
- **Consequence:** Superseded by D-131 implementation; preserved as architectural reference.

## D-127 — Render Free pilot with existing Supabase Auth and PostgreSQL

- **Date & Author:** 2026-10-03 — Codex (OpenAI)
- **Status:** decided-not-provisioned
- **Context:** Hard free-tier constraint, 2-3 users, simple hosting without external Redis or object storage.
- **Decision:** Selected Render Free Docker Web Service (host-supervised API + worker) + existing Supabase (Auth + PG pooler). 30-day bounded retention for cache and runs. Startup Alembic migrations.
- **Trade-off:** Render Free sleeps after 15m inactivity, 512MB RAM, no headless Chromium verification. Pilot only; Azure VM unaffected. Documented in `docs/deployment/version-2/free-tier-migration-guide.md`.

## D-126 — Railway Hobby as the recommended Version 2 hosting target

- **Date & Author:** 2026-10-03 — Codex (OpenAI)
- **Status:** decided-not-provisioned
- **Context:** Simpler managed alternative to self-hosted Azure VM Compose architecture.
- **Decision:** Recommended Railway Hobby (web service, dedicated worker, and managed PG) + Supabase Google Auth. Same-origin previews and PG job queue retained.
- **Trade-off:** Paid/metered; operator-owned database backups. Documented in `docs/deployment/version-2/deployment-strategy.md`.

## D-125 — Structure-preserving PDF intake with bundled OCR

- **Date & Author:** 2026-10-02 20:35 +05:30 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** Full-page OCR degraded digital PDFs, while layout-free text extraction failed on scanned resumes.
- **Decision:** Docling PDFium backend for digital text + RapidOCR for scanned regions. Exports structured Markdown hierarchy. Bundled offline models at `/opt/docling-models`. Full transcript is user-editable before Discovery submission.
- **Rejected alternatives:** Cloud OCR dependency; raw binary file storage; DOCX/photos deferred. Supersedes D-124 OCR deferral.

## D-124 — Owner reset and text-first Discovery file intake

- **Date & Author:** 2026-10-02 18:05 +05:30 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** Users required ability to restart portfolio from scratch and submit resume files directly.
- **Decision:** Added owner-scoped reset action in sticky header; purges session state, jobs, runs, versions, and chat while retaining session ID. Upload adapter extracts text from PDF/MD/TXT into `document_text`.
- **Consequence:** Running workers fenced by revision check; uploaded binaries discarded after text extraction.

## D-123 — Shared model layer generalised for a third engine

- **Date & Author:** 2026-10-02 09:43 +05:30 — Claude Code (Anthropic)
- **Status:** decided-implemented-locally
- **Context:** Model routing and per-run allowances were hardcoded for two engines (Discovery and Content Architect).
- **Decision:** Added `AgentKey.CODE_GENERATOR` with engine preflight, timeout validation, and `recovery_allowance = 0`. JSON parser supports raw control chars (`strict=False`) for markup strings.
- **Consequence:** Third engine integrated cleanly into model client and budgeting. Unconfigured engines fail closed.

## D-122 — Studio: a one-shot, verified page build with sealed versions and a sandboxed same-origin preview

- **Date & Author:** 2026-10-02 09:43 +05:30 — Claude Code (Anthropic)
- **Status:** decided-implemented-locally
- **Context:** Content Architect approval was terminal; required page generation, verified preview, and chat edits without unconstrained retry/repair loops.
- **Decision:** Single durable job per build (single attempt). Host-owned `<head>`, strict closed-world body validation, DB-sealed bundle, optional browser verification. Structured failure envelope (no live overwrite on failure). Sandboxed preview (`/preview/g/<hmac>...`) with CSP sandbox (no scripts, no same-origin). Chat edits apply typed content mutations and rebuild. One-click "Approve & generate my portfolio" CTA.
- **Rejected alternatives:** Model-written `<head>`; auto-fixing near-misses; BS4/html5lib dependency; external object stores or public hosting.
- **Consequence:** Safe, deterministic, verifiable page generation with immutable version audit trail.

## D-121 — Preview belongs to the Code Generator, not Content Architect

- **Date & Author:** 2026-10-01 21:55 +05:30 — Claude Code (Anthropic)
- **Status:** decided-and-implemented-locally
- **Context:** Content Architect had an unverified client-side preview tab; operator mandated previews happen only in Code Generator.
- **Decision:** Removed client-side preview from Content Architect. Reference theme moved to `docs/pinned-theme/`. Content Architect review strictly inspects copy, evidence, and coverage.
- **Consequence:** Previews restricted exclusively to verified Studio bundles.

## D-120 — Compact Discovery draft with bounded same-route recovery

- **Date & Author:** 2026-10-01 16:25 +05:30 — Codex (OpenAI)
- **Status:** decided-implemented-locally
- **Context:** Strict span-linked dossier emission was slow and fragile; single model lane created queue contention.
- **Decision:** Model emits compact draft; host builds `DiscoveryDossier/v1` and repairs IDs/links. Single same-route recovery attempt, streaming support, and configurable model-lane concurrency (migration 0026).
- **Consequence:** Supersedes D-116 strict span emission. Fast, reliable brief generation.

## D-119 — Content Architect routes through GPT-6 Luna

- **Date & Author:** 2026-10-01 14:30 +05:30 — Claude Code (Anthropic)
- **Status:** decided-and-implemented-locally
- **Context:** Operator requested Content Architect use GPT-6 Luna while Discovery keeps its existing model.
- **Decision:** Added `experiential_luna_6` profile in `config/models.toml` for Content Architect routes (`active_agent_routes_v3`). Single-provider rule preserved.

## D-118 — Typed single-page content tree for the pinned template

- **Date & Author:** 2026-10-01 13:05 +05:30 — Claude Code (Anthropic)
- **Status:** decided-and-implemented-locally
- **Context:** Content Architect emitted generic multi-route sites mismatching the pinned single-page template.
- **Decision:** Emits typed `page_content` matching template regions (4 pillars, organization names, structured slots). Claims and 6-way coverage ledger bind to field paths. Repaired via single integration call.
- **Consequence:** Exact structural alignment between content plan and theme markup.

## D-117 — Single-provider routing for active agent operations

- **Date & Author:** 2026-10-01 10:40 +05:30 — Codex (OpenAI)
- **Status:** decided-and-implemented-locally
- **Context:** Transient primary failures triggered cross-provider fallbacks with confusing error messages.
- **Decision:** Active stages (Discovery and Content Architect) use only the configured primary profile; alternate-provider fallbacks disabled.
- **Consequence:** Deterministic provider routing and transparent failure reporting.

## D-116 — Complete agent handoffs with two approvals and AI-written HTML

- **Date & Author:** 2026-09-29 16:13 +05:30 — Codex (OpenAI)
- **Status:** decided-not-yet-implemented (foundational; refined by D-118, D-120, D-122)
- **Context:** Architectural vision for 3-stage portfolio pipeline with text-first intake, explicit reviews, and verified build.
- **Decision:** Freeform text intake -> Discovery dossier (approval 1) -> Content Architect page plan (approval 2) -> Code Generator verified HTML bundle.
- **Consequence:** Foundation of the 3-stage portfolio pipeline.

## D-115 — Research-only refinement of the portfolio proposal

- **Date & Author:** 2026-09-29 01:22 +05:30 — Codex (OpenAI)
- **Status:** open / historical-research
- **Context:** Architecture research proposal in `docs/architecture/10-...` through `13-...`.
- **Decision:** Groundwork for evidence contracts, fixed-CSS rendering, verified preview, and bounded repair without altering active runtime.
- **Consequence:** Predecessor to D-116.

## D-138 — Measured generation speed with configured timing context

- **Date & Author:** 2026-10-06 — Codex (OpenAI)
- **Status:** implemented-locally; Render release requires operator approval
- **Context:** The operator reported slow Explorer and Content Architect results on Render Free and requested faster generation, a shorter Studio animation, and visible estimates without changing working behavior.
- **Decision:** Keep configured models, token budgets, explicit stage actions and the existing hosting plan. Adopt low Content Architect reasoning after uncached sparse/rich sample comparisons and strict output/render validation. Retain conditional writing/integration and all grounding/coverage gates. Reduce idle worker polling to two seconds while preserving the small-host concurrency/pool limits. Include the pending host renderer and sparse-content fixes from D-133; validate sample disclaimers in the required section headings. Reduce the Studio hold and preview-loading bound by five seconds, while unfinished actual builds remain in progress.
- **Presentation:** Expose only non-secret timing ranges from application configuration. Show a typical range alongside actual elapsed time, with queue and overrun explanations. Ranges are estimates, not a completion deadline; this refines the timing presentation in D-135 at the operator's request.
- **Evidence:** The dated local comparisons and quality checks are recorded in `docs/performance-follow-ups.md`; opt-in scripts use repository samples and never run as standard tests. Content-free queue/handler/model timing logs enable post-release measurement.
- **Rejected alternatives:** Changing providers/models, trimming source facts or output limits, weakening validators, introducing another queue, increasing Free-instance concurrency, or promising to eliminate Render's idle wake-up.
- **Consequence:** Local measured speed improves while source validation and user approvals remain intact. Live warm/cold timings still require a separately approved Render release and observation.

## D-139 — External health checks mitigate Render Free idle sleep

- **Date & Author:** 2026-10-06 — Codex (OpenAI)
- **Status:** configured externally with operator authorization; application deployment remains pending
- **Context:** The operator chose the free external scheduler after reviewing Render's inactivity shutdown and monthly runtime limits.
- **Decision:** Use one enabled cron-job.org HTTPS GET to the existing `/health/live` endpoint every five minutes, with saved responses and sustained-failure, recovery and deactivation notifications. Keep Render's dependency readiness check, existing compute plan, durable PostgreSQL queue and combined API/worker launcher.
- **Rejected alternatives:** An in-process or local-PC timer cannot operate independently when its host stops; GitHub schedules lack reliable timing; a paid Render Cron Job adds cost while retaining Free web-service limitations. No agent endpoint is invoked to keep the app awake.
- **Evidence and limits:** The saved settings, external request results and management links are recorded in `exa-results/render-idle-strategy-2026-10-06.md`. The setup mitigates inactivity sleep without guaranteeing availability or removing shared runtime quotas, platform restarts, crashes or scheduler failures. Paid compute and application release still require separate operator authorization.

## D-140 — Content-sized sign-in examples and one owner for Google feedback

- **Date & Author:** 2026-10-06 — Codex (OpenAI)
- **Status:** implemented-locally; application release requires operator approval
- **Context:** The operator reported overlapping text and broken animation on the welcome page containing the Google sign-in button. Fixed card heights clipped sample copy and layered cards exposed competing text; the showcase separately reset the authentication button.
- **Decision:** Keep the existing sign-in shell, bundled typography, example portfolios and Google authentication flow. Reserve enough grid space for all sample cards while exposing only the selected card. Use a short entrance, pausable rotation, manual keyboard controls, offscreen/hidden-page pausing and reduced-motion support. Label the content as examples rather than simulate agent work. Let the authentication controller own loading feedback and place sign-in errors beside the button.
- **Rejected alternatives:** Smaller text to force overflow into fixed boxes, overlapping readable cards, pointer tilt and competing status loops, a new animation dependency, or authentication controls owned by decorative JavaScript.
- **Consequence:** Welcome copy and examples remain readable as screens and text sizes change. Authentication and stage boundaries remain intact; browser checks use a mocked provider and do not initiate real Google login.

## D-141 — Full CI on staging, same-SHA reuse on deployment

- **Date & Author:** 2026-10-06 — Claude Code (Anthropic)
- **Status:** implemented-locally; first live proof requires a staging push
- **Context:** One serial CI job ran on every push to every branch and again on `deployment` for a commit already proven on `staging`, making each release wait for a duplicate full run.
- **Decision:** Run CI only on pushes to `staging`/`deployment`, on pull requests to `staging`/`main`, and manually. Split the work into parallel jobs behind an always-running aggregate job that keeps the original `quality` id and display name for the branch ruleset. On `deployment`, a `gate` job passes the check immediately when the exact SHA already has a successful staging push run; otherwise the full suite runs. Docker build/smoke runs only when Docker-relevant paths change (or manually). Superseded runs are cancelled except on `deployment`.
- **Rejected alternatives:** Staging-only CI (no protection for SHAs pushed straight to deployment), deployment-only CI (late feedback), path-level `paths-ignore` (leaves required checks pending).
- **Consequence:** Releases of a verified SHA become near-instant; unverified hotfixes still get full verification. Nightly scheduled audits were not added.

## D-142 — Claret Marquee: a fifth look on the shared Atlas content path

- **Date & Author:** 2026-10-07 — Claude Code (Anthropic)
- **Status:** implemented-locally; no release. The sealed manifest is a development seal until a release is approved.
- **Context:** The operator asked for a premium, completely different look than Cobalt & volt (scroll-driven motion, depth backgrounds, strong type) that works with the unchanged Content Architect and Studio, appears in Explorer, and looks complete without a photo.
- **Decision:** Add immutable theme `claret-marquee/v1` (Bodoni Moda, Hanken Grotesk, DM Mono, all self-hosted OFL; claret and amber) as a fifth Explorer card, host-rendered with its own standalone contract. One keyframes definition drives scroll scenes through either native scroll timelines or a JS scrubber, so engines without scroll-driven animation behave identically; reduced motion, no-script and webdriver runs get the finished page. Replace the six literal `cobalt-atlas/v2` content gates with `themes.uses_atlas_content`. Add manifest `runtime.global` (default `AtlasTheme`) for the verifier, and poll with `evaluate` because string predicates are blocked by the preview CSP.
- **Rejected alternatives:** Replacing a current look; a Swiss monochrome poster look (the warm dark serif corner was the open gap); per-word or per-letter server markup (breaks the closed-world text rule and screen readers); GSAP/Lenis/WebGL; subclassing the Cobalt contract; a model-written body.
- **Consequence:** A new Atlas-content theme needs a package, a registry entry and one palette entry, with no prompt or agent change. Production browser verification is still off on Render Free, so the browser matrix in `tests/browser/test_claret_marquee_theme.py` is the guard. Released theme bytes are immutable: any later design change needs a new version.
