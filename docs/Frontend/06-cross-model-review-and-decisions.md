# Cross-model review log

> Status: complete (2026-09-02). This is a log of the review of the
> `docs/Frontend/` package requested directly by the project owner. It records
> what was checked, what was found, and exactly where each finding was folded
> into the primary documents. It intentionally does not duplicate content that
> now lives in `README.md`/`01`-`05` — read those directly; this file is
> provenance, not a second source of truth.

## How this review was done

Read directly, in full: `README.md`, `01-product-experience-and-information-architecture.md`,
`02-state-progress-and-edge-cases.md`, `03-visual-system-architecture-and-evidence.md`,
`05-implementation-blueprint-and-acceptance-matrix.md`, `docs/code-generator-architecture/free-host-deployment.md`,
`docs/Auth/04-deployment-and-operations.md`, `docs/architecture.md`. `04-research-evidence-and-pattern-analysis.md`
was reviewed at a research/skim level (external-source and hosting-evidence
sections), consistent with its own stated role as evidentiary backing for `01`-`03`.

Cross-checked directly against the running implementation, not just the research
package's own citations: `src/oryxenai/web/static/app-auth-bootstrap.mjs`,
`src/oryxenai/auth/static/auth-controller.mjs`, `src/oryxenai/auth/static/auth-runtime.mjs`,
`src/oryxenai/web/templates/base.html`, `src/oryxenai/web/static/app.css`
(the structural auth-hide rule), and `src/oryxenai/web/routes.py`. This mattered
because the package becomes build guidance for a smaller implementing model —
precision against real source beats a restated summary.

## Verdict

The research package was sound and moved forward largely as written. It already
satisfied the owner's core ask — visually advanced and modern without being
"generic AI slop" or heavy, minimal screens, a preview experience shaped like
emergent.sh/Lovable/Replit, and an explicit stance on preserving the working
auth flow. This review's real contribution: one concrete bug found in the
**current, already-shipped** auth code (not the redesign), a precise account of
exactly which files the Preact migration is and is not allowed to touch, a
container-sizing recipe, and one resolved deployment conflict — all now
integrated below.

## Findings and where they now live

| Finding | Integrated into |
| --- | --- |
| Six open review questions, each resolved | `README.md` "Review resolutions" |
| Render + Cloudflare R2 confirmed as hosting target; AWS section in `docs/Auth/04` marked superseded | `README.md` decision 9; `03` §9; `05` §16 "Deployment target"; pointer documented in `docs/Auth/04-deployment-and-operations.md` |
| Bug: `resolveAuthenticatedContext()` (gates `/app`) force-signs-out on `AUTH_PROVIDER_UNAVAILABLE`/`MODEL_PROVIDER_CREDIT_EXHAUSTED` instead of the safe in-place message `routeController()` already shows for the same codes | `05` §19 Phase 1 (fix first, independently); `02` §6 auth edge-case table (new row) |
| `app-auth-bootstrap.mjs`'s hardcoded `import("/static/app.js")` must change to the new bundle, branched on `isDeveloperPage`; `bootProductShell()` itself needs no behavioral change if the Preact entry keeps the `{ boot, stop, restart }` shape | `05` §19 Phase 1 |
| `body.auth-pending` structural hide rule (`app.css:354`) must get an explicit home in the new stylesheet layer before `app.css` is retired | `05` §19 Phase 1 |
| Preview container-sizing recipe: reserve the box via `aspect-ratio`/fixed size before load (CLS); letterbox via a fixed-size wrapper plus `transform: scale()`, never by resizing the iframe outside the four verified profiles | `02` §8 "Route and viewport controls"; `05` §8.10 `PreviewSurface`; `05` §19 Phase 4 stop gate |
| Preview-gateway cold-start copy should mirror the auth loader's two-second acknowledgment, since it's a separate Render service that sleeps independently | `03` §5 "Preview load" |
| Vite manifest resolution guidance (`manifest: true` + a small Python resolver) | `05` §16 |
| Stray pasted path/filename fragment; stale "React/Next.js" and "auth not present" lines | `docs/architecture.md` (fixed directly) |

## Note on the owner's mid-review design-style comment

Partway through this review the owner added, unprompted and explicitly marked
as optional ("it is up to you to take it or completely remove it"), a design
style described as something transcribed as *"I'm struggling"*, which does not
parse as a recognizable named style — most likely a voice-to-text artifact.
Rather than guess at a phrase that can't be confidently decoded, the review
treated the surrounding, clearly-stated intent (advanced, modern, not complex,
not generic AI slop) as the real requirement, and confirmed that intent is
already what "Editorial Swiss — The Living Draft" (`README.md`, `03` §1) was
built to satisfy. Flagged here plainly rather than silently discarded.

## What happens next

Per this project's own multi-agent protocol, the remaining step is: once the
owner confirms direction, log a `DECISIONS.md` entry formalizing Preact +
TypeScript + Vite as the accepted product frontend stack and Render +
Cloudflare R2 as the accepted hosting target, plus a `CHANGES.md` entry for
this review. That has not been done yet — it needs explicit sign-off, not an
assumption.

No code was written, no build tooling was installed, and no agent/Preview
backend behavior was touched in the course of this review.
