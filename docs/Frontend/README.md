# OryxenAI frontend research

> Status: implemented for the authenticated three-agent release (2026-09-04).
> The current `/app` boundary is Discovery, Content Architect, and Visual Design
> Director only; Build Preparation, Code Generator, and Preview remain deferred
> product phases while their backend and development surfaces continue separately.
> See `DECISIONS.md` D-063 and
> [06-cross-model-review-log](06-cross-model-review-and-decisions.md) for the review
> record and implementation-safety corrections. The later-stage material in this
> package is retained as deferred research, not current `/app` scope.

## Recommendation in one sentence

Build OryxenAI as a light, single-portfolio **studio that changes posture as the
portfolio advances**: conversational during Discovery, document-oriented during
Content and Design review, and explicit about ending this release at an approved
creative handoff.

This is deliberately not a chatbot wrapped around a dashboard and not a browser
IDE. The user is producing one portfolio through a sequence of explicit decisions.
The interface should make that sequence, the current decision, and the trustworthy
result obvious.

## How to use this package

| Document | Primary question |
| --- | --- |
| [Product experience and information architecture](01-product-experience-and-information-architecture.md) | What does the user see and where do they go? |
| [State, progress, and edge cases](02-state-progress-and-edge-cases.md) | How does every durable state become honest UI behavior? |
| [Visual system, architecture, and evidence](03-visual-system-architecture-and-evidence.md) | How should it look, remain light, and be built later? |
| [Research evidence and pattern analysis](04-research-evidence-and-pattern-analysis.md) | What repository, competitor, visual-style, web-platform, accessibility, and hosting evidence supports the direction? |
| [Implementation blueprint and acceptance matrix](05-implementation-blueprint-and-acceptance-matrix.md) | What exact routes, endpoints, adapters, components, failures, tests, and rollout gates should implementation follow? |

### Coverage map

| Concern | Primary document | Supporting detail |
| --- | --- | --- |
| Auth, onboarding, entry, and return flow | 01 | 02 edge cases; 05 route/API/test contract |
| Home and product mental model | README, 01 | 04 repository synthesis |
| Agent sequence and explicit handoffs | 01 | 02 state maps; 05 adapters/actions |
| Discovery conversation and brief | 01 | 02 edge cases; 05 endpoint/component contract |
| Content and Design artifact review | 01 | 02 state maps; 05 artifact/revision contract |
| Deferred Build Preparation product work | 02 | 04 evidence; 05 historical compatibility proposal |
| Deferred Code Generator product work | 02 | 04 evidence; 05 historical endpoint/adapter proposal |
| Deferred Preview product work | 01, 02 | 03 architecture; 05 historical validation proposal |
| Visual identity, theme, imagery, and motion | 03 | 04 style comparison and asset strategy |
| Performance and low-cost hosting | 03 | 04 platform findings; 05 measurable gates |
| Accessibility and responsive behavior | 02, 03 | 05 implementation acceptance |
| Errors, recovery, refresh, and multi-tab behavior | 02 | 05 choreography and tests |
| Implementation sequence and completion criteria | 03 | 05 rollout stop gates and full matrix |

The documents distinguish five evidence labels:

- **Repository evidence** — behavior read from application code, API schemas,
  decisions, and architecture documents.
- **Direct observation** — behavior observed in the local browser interface.
- **External evidence** — behavior documented by the referenced product or web
  platform owner.
- **Recommendation** — the proposed OryxenAI product decision.
- **Unknown** — a capability or contract that is not safely available to the
  product frontend.

The supplementary context supplied with the request was used only to identify
questions worth checking. It is not cited as evidence.

## Product truth that shapes the interface

These are the constraints with the largest UX consequences. Verify them against
the linked source areas before implementation because agent and infrastructure
work continues independently.

### One durable portfolio, not a project dashboard

For a normal user, the entitlement projection and session routes define one
canonical portfolio session, one generation variant, and a read-only state after
a successful preview. Administrators have separate cross-session powers. The
authoritative sources are:

- `src/oryxenai/auth/schemas.py`
- `src/oryxenai/auth/entitlements.py`
- `src/oryxenai/api/routes/sessions.py`
- `docs/Auth/01-user-flows-and-route-contract.md`

Therefore the authenticated entry experience should answer “start or continue my
portfolio,” not “which project or conversation do I want?” A grid of fake projects,
recent chats, templates, and team workspaces would introduce a product model the
system does not have.

### The sequence is explicit and gated

The current authenticated product sequence is:

```text
Discover -> Content -> Design -> Creative handoff saved
```

The user-facing names are intentionally shorter than the implementation names:

| User-facing milestone | Backing system | Completion boundary |
| --- | --- | --- |
| Discover | Discovery | Approved brief |
| Content | Content Architect | Approved content plan |
| Design | Visual Design Director | Approved visual direction |

Every agent begins through an explicit call. Approval of one stage must reveal a
clear continuation action; it must not imply that the next stage started
automatically. Approval of Design is terminal in `/app`: it records a creative
handoff and does not call Build Preparation or Code Generator.

Build Preparation, Code Generator, and Preview remain implemented or researched
outside this release boundary. Their production APIs retain server authorization,
and their existing developer harnesses remain available for development. They must
not appear in the authenticated product until a later release decision explicitly
adds them.

Authoritative source areas:

- `src/oryxenai/agents/discovery/`
- `src/oryxenai/agents/content_architect/`
- `src/oryxenai/agents/visual_design_director/`
- `src/oryxenai/agents/build_preparation/`
- `src/oryxenai/agents/code_generator/`
- `DECISIONS.md`

### Deferred Preview still means verified preview

The product may embed only the active, promoted build. Generation does not expose a
hot-reloading candidate, unverified source tree, or temporary development server.
If a later attempt fails, the prior active preview remains active. Preview runs on
a separate opaque origin and is treated as untrusted generated content.

The product preview toolbar is intentionally bounded to:

- promoted route selection;
- mobile, tablet, desktop, and fit viewport modes;
- refresh; and
- open in a new tab.

Public publishing, custom domains, analytics, deployment history, and share links
are separate product decisions. The interface must say **Preview**, not “Published,”
“Production,” or “Live site.”

Authoritative source:
`docs/code-generator-architecture/live-preview-and-deployment.md`.

### The frontend knows state, not private reasoning

The APIs expose durable statuses, selected safe events, failures, and promoted
artifacts. They do not expose a trustworthy percentage or the model’s private
reasoning. Progress must use semantic milestones and plain status copy. It must
never manufacture “thinking” steps, token streams, or exact completion estimates.

### Authentication is a product flow

Authentication is Google-only through Supabase, followed by server-authoritative
admission and optional username onboarding. The controller already distinguishes
signed-out, callback, denied, unavailable, onboarding, normal app, and admin states.
The redesign should preserve that route and security behavior while replacing the
temporary visual shell.

Authoritative sources:

- `src/oryxenai/auth/web.py`
- `src/oryxenai/auth/static/auth-controller.mjs`
- `src/oryxenai/auth/static/auth-runtime.mjs`
- `docs/Auth/01-user-flows-and-route-contract.md`
- `docs/Frontend/06-cross-model-review-and-decisions.md` §3 — a migration-safety
  checklist and one corrected bug in the current implementation, found by reading
  the auth controller and runtime side by side.

## Chosen product model

### The portfolio studio

`/app` is both authenticated home and working studio. It selects the right posture
from server state:

```text
No portfolio     -> a focused start surface
Incomplete       -> resume the current decision or active run
Needs attention  -> show recovery before secondary content
Design approved  -> preserve the three approved artifacts and creative handoff
```

There is no permanent three-column control room. The visible hierarchy changes
because the user’s job changes:

| Phase | Dominant surface | Secondary surface |
| --- | --- | --- |
| Discovery | Conversation and one current question | Intake/brief summary |
| Content review | Readable content artifact | Revision composer |
| Design review | Visual-direction artifact | Revision composer |
| Complete | Creative handoff confirmation | Journey and approved artifacts |

### Agentic without looking like a chatbot

The AI character comes from observable handoffs, not decorative AI imagery:

- one journey line shows work passing between specialized stages;
- completed artifacts remain inspectable as durable outputs;
- the current stage explains what it is doing in user language;
- user decisions receive stronger visual weight than background work; and
- the final approved direction is visibly treated as a saved creative handoff.

Chat is used only where the backend supports conversational input. Content and
Design are run/review interfaces, not empty chat boxes waiting for unsupported
follow-up prompts.

## Visual premise: Editorial Swiss - The Living Draft

The interface should feel like an editorial draft becoming a finished portfolio:
warm paper, precise dark type, restrained technical annotations, and a single blue
handoff line that advances only when durable state advances.

Editorial is the identity, Swiss design supplies the grid and typographic discipline,
and minimalism is the restraint rule. A restrained futuristic quality appears only
in exact state transitions and the verified Preview frame. Maximalist, Y2K, pixel,
clay, glassmorphism, cyberpunk, and raster-collage treatments are not used in the
core product because they compete with artifact readability, trust, or performance.
Ambiguous style labels are not silently interpreted.

The signature is the **living draft line**. It connects the journey milestones and
briefly sweeps forward after a confirmed state transition. The same geometry can
appear as a tiny inline SVG while authentication or the application shell resolves.
It is not an ambient particle system, glow, or looping neural-network animation.

The premise avoids the most interchangeable AI-product cues:

- no purple-blue gradient hero;
- no glass panels floating over blurred color blobs;
- no sparkle or robot iconography;
- no grid of equally weighted rounded cards;
- no theatrical “analyzing your brilliance” copy; and
- no developer telemetry presented as product progress.

The detailed palette, typography, spacing, motion, and component rules live in the
[visual and architecture document](03-visual-system-architecture-and-evidence.md).

## Decisions made in this research

1. Keep one server route for the product shell and use small, validated URL query
   state for stage and preview deep links. Do not add a client router.
2. Preserve lightweight server-rendered authentication pages; use a small component
   client only for the stateful `/app` studio.
3. Recommend Preact, TypeScript, and Vite for that studio. The existing single
   `app.js` has outgrown a safe monolith, while a full application framework and
   component ecosystem would add little value to this product model.
4. Normalize agent payloads through frontend adapters. Components consume a small
   journey vocabulary instead of branching on every backend status.
5. Keep polling because it is the available contract. Make it visibility-aware,
   abortable, and centrally owned; do not assume streaming.
6. Make light mode the initial authored experience. A dark theme is deferred until
   the primary interface is proven and measured.
7. Use a self-hosted display-font subset, inline SVG icons, and CSS motion. No
   remote font, illustration, icon, or animation runtime is required.
8. Ship no required raster art in the authenticated product shell. Use one small
   code-native construction-line SVG, editorial composition, and the generated
   portfolio itself as the primary visual material.

9. End the current normal-product UI after approved Visual Design Direction.
   Preserve later-stage backend authorization and keep development-harness auth
   independently configurable; see `DECISIONS.md` D-063.
10. Target Render-style free web hosting plus the existing Cloudflare R2 artifact
   storage for the deployed product, per
   `docs/code-generator-architecture/free-host-deployment.md`. Treat the early AWS
   contingency in `docs/Auth/04-deployment-and-operations.md` as superseded
   unless explicitly revisited.

These recommendations were reviewed on 2026-09-02 (see
[06-cross-model-review-log](06-cross-model-review-and-decisions.md)); the current
three-agent release boundary is recorded in `DECISIONS.md` D-063.

## Explicit non-goals

The product frontend must not imply support for:

- multiple user projects, chats, branches, or collaborators;
- automatic stage chaining;
- model selection in the normal user experience;
- cancellation, pause, steering, or queued follow-up instructions;
- visual element selection or screenshot-to-prompt editing;
- a source-code editor or file browser;
- arbitrary downloads from generated content;
- user-visible version history or rollback;
- public portfolio deployment or custom domains;
- Build Preparation, Code Generator, or Preview controls in the current
  authenticated product;
- exact progress percentages or time remaining; or
- raw internal logs, provider names, storage vendors, hashes, or stack traces.

Developer harnesses may continue exposing development detail at their existing
protected or detached routes. They are evidence about backend behavior, not the
normal-user product design.

## Review resolutions

These were reviewed on 2026-09-02 (full reasoning in
[06-cross-model-review-log](06-cross-model-review-and-decisions.md) §1):

- Does the portfolio studio feel appropriate for a nontechnical creator?
  **Accepted.**
- Is the warm editorial direction right for the OryxenAI brand? **Accepted** —
  the one item that stays a taste call the owner keeps final say on, since there
  is no prior OryxenAI brand to compare against.
- Is a light-first release acceptable without a dark theme? **Accepted.**
- Are Content and Design artifacts understandable enough for meaningful approval?
  **Provisionally accepted** — confirm once Phase 2's stop gate (05 §19) runs
  against real agent output, not a fixture.
- Is the distinction between Preview and future publishing unmistakable?
  **Accepted.**
- Are the proposed bundle budgets strict enough for the intended hosting profile?
  **Accepted**, now that the hosting target is confirmed as Render + Cloudflare R2
  (see decision 9 above).

Implementation may proceed per 05's phased sequence without changing the agent or
preview architecture, with the two safety corrections in 06 folded into Phase 1
(auth continuity) and Phase 4 (Preview) of that sequence.
