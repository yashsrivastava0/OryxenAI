# Code Generator Reliability Repair Plan

## 1. Objective and findings

Make Code Generator consistently turn valid, approved Build Preparation briefs into complete, attractive portfolios that build, behave correctly, and pass verification before becoming the frontend preview.

This is a targeted repair of the existing generator—not a replacement of the agent pipeline. Keep the durable jobs, approved-brief hashes, resource acquisition, progressive generation, provider-neutral model boundary, and atomic preview promotion.

The investigation confirmed problems in both generation and verification:

| Confirmed problem | Consequence |
|---|---|
| The Python comment stripper mistakes JavaScript regular expressions for comments. | Valid content references disappear during validation and produce false “missing content” failures. |
| Final repair can receive no source code and an incorrect directory such as `src/routes/home/**`. | The model cannot inspect or edit the actual hashed section files responsible for a failure. |
| Runtime checks use planned resources without consistently accounting for acquisition fallbacks. | An intentional local substitute can fail an image requirement that no longer matches the implementation. |
| Font verification treats an unused, unloaded font weight as broken. | A valid local font fails verification; explicitly loading the retained example resolved the reported failure. |
| Motion verification compares authored transforms with browser-computed matrix strings. | Correct animations can fail because equivalent representations do not match textually. |
| Responsive layout and navigation expectations disagree with generation instructions. | The generator and verifier enforce different contracts. |
| Repair replaces the working source before all candidate checks finish. | A rejected repair can leave source and checkpoint records inconsistent. |
| Several tests use outdated fixtures. | They fail before reaching the worker behavior they are supposed to test. |

The focused baseline reproduced all five failures described in the handoff: one generator unit-test failure and four API/worker-flow failures. This was not a full-suite verification.

Visual quality is also not conclusively achieved. The retained screenshots show a coherent direction, but some imagery is unrelated to the portfolio and some controls are crowded. Preserve the stronger design work while testing this pillar independently.

No repository implementation changes or live OpenAI generations were made during this investigation.

## 2. Architecture and contract changes

### One executable contract for generation and verification

Introduce a versioned `ResolvedExecutionContract`, compiled after resource acquisition from:

- The immutable, hash-checked brief pair.
- The validated experience blueprint.
- The compiled work graph and actual file ownership.
- The final resource ledger, including substitutions.

This becomes the shared source for generation instructions, source audits, repair context, browser expectations, and quality review. These consumers must not independently reinterpret the same requirement.

The contract will contain:

- Exact route, section, content, resource, interaction, and motion identities.
- Actual generated file paths and ownership.
- Required navigation edges, distinct from the set of allowed destinations.
- Materialized resources or explicit fallback implementations.
- Per-breakpoint physical layout expectations.
- Observable browser evidence and the source owner responsible for it.

Preserve the original approved requirements separately. Resolving an implementation must never silently rewrite approved content or excuse an unmet required behavior.

### Version the changed semantics

Use a new blueprint schema for the responsive-layout changes and activate them under `code-generator-v6`.

- Centralize version dispatch in the existing pipeline-contract helpers.
- Update planning schemas, provider preflight, source metadata, queue namespaces, worker-release fencing, and checkpoint compatibility together.
- Retain historical readers for existing runs.
- Never reinterpret a stored older blueprint using the new layout semantics.
- Old workers must not claim new-contract jobs.
- An older incompatible failed run requires an explicit fresh generation, not an invisible migration or another charged attempt.

The Markdown Build Preparation input contract remains unchanged. No upstream agent redesign is required.

### Keep public APIs stable

Keep the existing session start, retry, regenerate, and state endpoints.

Add only safe, additive result information:

- Structured diagnostics with actionable ownership and browser evidence.
- Recorded resource substitutions.
- Accepted source/checkpoint identity.
- Verification and preview-promotion receipts.

Keep internal prompts, private documents, credentials, and unrestricted source context out of public responses.

## 3. Implementation sequence

### Step 1 — Establish regression fixtures and protect the remaining credit

First capture privacy-safe, minimal reproductions of the confirmed defects. Tests should initially demonstrate each failure before its fix.

Repair the stale tests without weakening production admission:

- Generate current fixtures through the actual brief compiler so section IDs and ownership match production.
- Make legacy compatibility tests explicitly use their legacy contract.
- Update the resource-materialization test to assert the current receipt shape, actual file existence, and hash preservation.
- Ensure worker tests reach their named checkpoint, redelivery, pause/resume, or promotion behavior.

Before any live call, introduce a resumable evaluation campaign with a **$3 total ceiling**, leaving **$1 of the stated $4 untouched**.

- Keep model selection in `config/models.toml`; use the configured OpenAI profiles.
- Supply verified USD pricing for every role used by Code Generator. Existing “configured credits” must not be interpreted as dollars.
- Reuse the existing budget wrapper, but calculate settlement from token usage and the campaign’s pricing snapshot.
- Reserve conservative input cost plus the operation’s maximum output allowance before sending a request.
- Include director, planner, resource-selection, generation, review, repair, and any necessary provider-preflight calls.
- Disable hidden SDK retries for this campaign. An explicit retry needs a new reservation.
- Treat missing usage or an interrupted request as consuming its full reservation.
- Refuse a call whose full reservation does not fit; do not squeeze a source-generation response into an unusably small token allowance.

Use a single-writer campaign runner with a lock and atomically persisted ledger in the ignored workspace. It must invoke the real shared workflow through a role-aware budgeted model factory—not substitute fixtures for live output. Persist reservations before transmission so restarting the runner cannot reset spending.

This is an evaluation safeguard, not a new billing subsystem. Its ceiling covers this campaign, not unrelated activity using the same API account. Verify rates immediately before execution using [OpenAI’s official pricing](https://developers.openai.com/api/docs/pricing), and reconcile returned usage as recommended in [OpenAI’s production guidance](https://developers.openai.com/api/docs/guides/production-best-practices#text-generation).

### Step 2 — Correct source and content validation

Make the existing TypeScript compiler-based audit the authoritative parser for executable JS/TS/JSX/TSX evidence.

- Remove comment-stripped substring scanning as an authority for content-use and executable-marker checks.
- Extend the existing AST audit to return structured findings with exact files and source locations.
- Preserve import resolution, route reachability, alias handling, and rendered-component evidence.
- Keep Python checks for filesystem safety, ownership, forbidden files, and other non-language concerns.
- Do not upgrade the scaffold’s pinned TypeScript merely to implement this change. Its existing compiler APIs support the required parsing and traversal. [TypeScript compiler API documentation](https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API)

Negative checks must remain meaningful: comments, orphan files, unused helpers, and decorative marker strings must not satisfy a requirement for rendered content.

Strengthen the content boundary:

- Reject duplicate section headings and normalized-ID collisions instead of silently overwriting content.
- Preserve Unicode, nested arrays/objects, numbers, booleans, and optional values in the typed content tree.
- Compile a recursive inventory separating display copy, destinations, and structural metadata.
- Use deterministic classification for fields defined by the brief format; have the existing planning operation classify otherwise ambiguous fields using exact source pointers.
- Require complete inventory coverage. Do not silently omit nested project or experience content.
- Verify display copy in rendered content and destinations in actual behavior; do not require internal values such as CTA kinds to appear as visible prose.

Generate large repeated content from typed data rather than asking the model to transcribe every item repeatedly.

### Step 3 — Resolve resources into honest, consistent implementations

Compile resource expectations from acquisition outcomes, not the original wish list alone.

For each placement, record one disposition:

1. Materialized local resource, with hash and provenance.
2. Approved local substitute, with the reason and required visual/behavioral properties.
3. Unresolved required resource, which blocks successful completion.

Apply the user-approved fallback policy:

- Optional unavailable imagery may become a deliberate typographic or locally rendered composition.
- Optional font failures may use a coherent local/system stack.
- An unavailable reference component may become an accessible local implementation with the same required behavior.
- Optional motion may use a simpler tested effect while preserving visibility and interactions.

Do not use unrelated stock photography merely to fill a slot. Do not render empty gray placeholders as a “polished fallback.”

Keep controlled acquisition, download limits, provenance, and the existing bounded stale-pin recovery. Never turn failures into an unrestricted research or retry loop.

Generation, token compilation, source auditing, and runtime verification must consume the same resolved disposition. An acquired image that remains selected must actually be rendered; a fallback must have its own affirmative checks rather than simply being exempted.

### Step 4 — Make layout, navigation, and motion contracts implementable

Replace ambiguous layout requirements with physical, measurable ones:

- Specify columns, gap, and width bounds per breakpoint.
- Distinguish an abstract design grid from actual CSS grid tracks.
- Give text measure its own selector instead of measuring an entire image-and-text section.
- Require unique targets for single-element relationships.
- Define repeated collections explicitly; never silently select the first of several matches.

Use those same values in generated styles, prompts, and browser assertions. Do not lower thresholds merely to make the retained example pass.

Compile one navigation manifest:

- Allowed destinations are a safety boundary, not an instruction to display every possible link.
- Required links come from approved navigation and CTA intent.
- Include route navigation and section anchors.
- Use the existing route/resource/section URL helpers for root and mounted previews.
- Verify keyboard activation, hash navigation, back navigation, and direct route loading.
- Never invent a contact backend, download, or destination absent from the approved inputs.

Keep creative freedom in composition, typography, imagery, and section structure. Use tested scaffold primitives for recurrent behavior such as disclosure navigation, focus handling, content reveals, and reduced-motion support. For disclosure controls, preserve the expected button behavior and expanded state. [WAI disclosure pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)

Derive trusted motion-pattern expectations from their actual implementations. Do not let a separately authored expectation contradict the selected effect.

### Step 5 — Repair browser verification and diagnostic evidence

Separate stable-layout inspection from motion observation.

For stable-layout checks:

- Wait for application readiness, required fonts, and visible-image decoding.
- Scroll lazy-loaded regions into view before judging their resources.
- Sample geometry after it stabilizes.
- Preserve real overflow, clipping, overlap, unreadable text, missing content, and unusable-control failures.

For fonts:

- Explicitly load the contracted local family/weight before testing availability.
- Distinguish an unloaded face from a failed face.
- Verify intended typography roles against their actual selectors.
- Keep missing or corrupt font files as failures.

For motion:

- Observe load animations from navigation start, rather than inspecting only their finished state.
- Trigger viewport, hover, focus, and activation effects deliberately.
- Account for duration and delay using bounded polling.
- Compare numeric opacity and normalized transform matrices with documented tolerances.
- Check reduced-motion behavior separately; content and controls must remain available.

Use browser readiness and stability conditions rather than arbitrary sleeps. Playwright’s documented actionability checks provide the baseline for visibility and stability. [Playwright actionability](https://playwright.dev/docs/actionability)

Every runtime diagnostic must include:

- Gate and stable diagnostic code.
- Route and section/region identity.
- Selector and match count.
- Viewport.
- Expected and observed values.
- Responsible source owner and relevant files.
- Candidate hash and available screenshot evidence.

Aggregate repeated observations of the same defect, while retaining distinct elements and viewport evidence. A generic message about “an anchor” must not collapse unrelated failures.

### Step 6 — Make repairs informed, transactional, and bounded

Build repair targets from the compiled ownership graph.

- Resolve hashed route directories and actual section files; never reconstruct paths from raw route IDs.
- Include complete editable owner files, relevant styles, imported contracts, and shared-component interfaces.
- Separate read-only context from authorized write paths.
- Partition oversized work by owner; never silently truncate source at a character limit.
- Detect missing source or nonexistent allowed paths before spending on a model call.
- Route compiler/scaffold defects to deterministic host fixes, not model edits of generated route files.

Make each repair a transaction:

1. Persist the attempt and parent checkpoint identity.
2. Create an isolated candidate.
3. Apply changes only within authorized paths.
4. Run source, ownership, type, and affected behavior checks.
5. Reject regressions or invalid candidates without changing the accepted workspace.
6. Accept and atomically promote the candidate only after the relevant checks and worker fences pass.

A failed candidate must leave the previous accepted source byte-for-byte unchanged.

Persist every attempted repair, including rejected and interrupted attempts—not just successful repairs. Record fresh diagnostics and rejection reasons so the next attempt does not receive the original stale problem repeatedly.

Retain finite configured repair limits. Count failures and crash-interrupted attempts against those limits. Stop repeated no-progress proposals. Infrastructure failures, expired authorization, missing toolchains, and exhausted credit must not trigger source-repair prompts.

### Step 7 — Reorder expensive review and preserve preview integrity

For the new contract, use this order:

**Generate → cheap source/type checks → assemble → clean build → browser checks → quality review → bounded repair → affected checks again → final verification → preview promotion.**

Keep the existing quality floor. The change is to review a working candidate with useful evidence, rather than repeatedly reviewing broken source.

- Cache review results by source and resolved-contract hashes.
- Send owner-focused context for targeted defects.
- Invalidate downstream receipts whenever their input hash changes.
- Require final build, browser, and quality receipts to describe the same accepted candidate.
- Preserve the existing preview until its replacement has passed all gates.
- Retrying artifact upload or preview promotion must reuse an already verified artifact without another model generation.

Export real diagnostics, substitutions, repair outcomes, screenshots, and receipts. Failed-run exports must not replace the actual failure with placeholder messages or discard evidence needed to reproduce it.

## 4. Verification and live acceptance

### Offline regression coverage

Complete these groups before spending on live generation:

| Group | Required scenarios |
|---|---|
| Brief admission | Current approved brief pairs; Unicode; nested content; duplicate identities; malformed indexes; hash mismatch; configured scope limits. |
| Source audit | Regex literals containing slashes; templates; JSX attributes; comments; imported aliases; orphan files; missing rendered content. |
| Resources | Successful local assets; stale pins; unavailable optional media/fonts; corrupt required resources; recorded substitutions. |
| Browser behavior | Single-page and multipage navigation; section links; mobile disclosure; keyboard use; reduced motion; lazy images; unloaded font weights; equivalent transform matrices. |
| Repair | Correct hashed ownership; complete context; unauthorized writes rejected; candidate rollback; fresh feedback; no-progress stop; crash/redelivery accounting. |
| Durability and preview | Checkpoint reuse; duplicate job delivery; stale-worker rejection; entitlement changes; failed regeneration preserving the previous preview; promotion retry without regeneration. |

Exercise the existing mobile, tablet, and desktop verification sizes, plus a 320-pixel narrow-screen case and a 1280-pixel laptop case.

Test artifacts both at `/` and through the actual nested preview gateway. Include direct navigation to non-home routes and refresh. Existing Vite-relative asset handling must remain intact.

Run generator-focused tests first, followed by the canonical lint, format-check, type-check, and full test commands. Use only the dedicated test database for integration tests. Report unrelated failures accurately instead of changing unrelated systems.

### Two fresh live acceptance runs

After offline gates pass, use the real OpenAI workflow under the shared $3 campaign ceiling:

1. A dense single-page portfolio based on the retained approved input, exercising its actual content, resources, navigation, and motion.
2. A distinct privacy-safe multipage brief pair with nested project content, different visual direction, and an explicitly exercised optional-resource fallback.

Do not manually patch the exported portfolios. Fix generator code, contracts, or prompts and rerun through the actual workflow.

Each successful run must demonstrate:

- Complete approved content and working destinations.
- Clean build and passing source/runtime gates.
- A promoted preview whose artifact matches the verified candidate.
- No unexplained browser errors or missing local assets.
- Desktop and mobile screenshots reviewed for hierarchy, relevant imagery, readable typography, usable controls, and coherent motion.
- Recorded substitutions and actual campaign usage.

Use human screenshot inspection for visual acceptance; an additional paid vision-model loop is unnecessary for this budget.

If the remaining reservation cannot fund another required call, stop the campaign safely and report incomplete live acceptance. Do not spend the $1 reserve or claim validation that did not happen.

## 5. Completion criteria and boundaries

The repair is complete only when the regression fixes, transactional repair behavior, fresh end-to-end runs, and preview evidence above are verified—not merely when the existing tests pass.

During implementation:

- Work alone and preserve other contributors’ frontend/auth changes.
- Make task-scoped local commits at verified checkpoints.
- Record completed units in `CHANGES.md`, including its compaction check.
- Record the executable-contract and review-order changes in `DECISIONS.md`.
- Update stale generator documentation to match the implemented Markdown-brief workflow.
- Report commit hashes, verification results, preview references, spending, and remaining limitations. Do not push without authorization.

Defaults are OpenAI through configuration, a $3 evaluation ceiling, polished optional-resource fallbacks, and no automatic chaining or public deployment.

“Works correctly” means reliable handling of valid supported Build Preparation outputs, with complete content, verified behavior, and reviewed visual quality. It cannot honestly mean guaranteed success for unlimited input, unavailable infrastructure, or exhausted account credit. Those conditions must produce a truthful, recoverable state while preserving any existing working preview.
