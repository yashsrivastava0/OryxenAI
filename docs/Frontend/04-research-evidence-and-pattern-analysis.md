# Research evidence and pattern analysis

> Status: supporting research for the proposed OryxenAI frontend direction.
> Repository behavior remains authoritative. External products are comparisons,
> not specifications. Research was checked on 2026-09-02 unless noted otherwise.

## 1. Why this document exists

The first three documents state the recommended product model, state behavior,
visual system, and frontend architecture. This document preserves the wider
investigation behind those choices so useful findings are not lost when the team
moves from research to implementation.

It answers five questions:

1. What does the repository prove about the product today?
2. Which current product patterns are relevant, and which are not transferable?
3. Which visual direction best fits OryxenAI?
4. What should imagery, motion, loading, and polish look like without a heavy
   frontend?
5. Which conclusions are firm, provisional, or still unknown?

The attached brainstorming context from the original request was used to generate
questions. It is not evidence and does not decide any recommendation below.

## 2. Executive synthesis

The strongest direction is not a conventional chatbot, a developer IDE, or a
project dashboard. It is a **single-portfolio editorial studio** whose dominant
surface changes with the work:

- conversation when the person is supplying and clarifying source material;
- a readable document when the person must review content or design direction;
- an honest milestone view while deterministic or model-backed work runs; and
- the verified portfolio Preview when a promoted build exists.

The chosen visual thesis is **Editorial Swiss: The Living Draft**:

- **Editorial** supplies warmth, story, readable artifacts, and a sense that the
  person's material is being shaped into a finished publication.
- **Swiss/International Typographic Style** supplies the grid, typographic hierarchy,
  alignment, labels, and disciplined information density.
- **Minimalism** is a constraint, not the identity: every visible object must carry
  meaning, but the result must not become anonymous or sterile.
- **Futuristic** influence appears only in exact state feedback, the moving handoff
  line, and the verified Preview frame. It does not become neon science fiction.

This combination is distinctive through proportion, language, rhythm, and one
recognizable line motif. It does not require raster hero art, video, WebGL, large
component libraries, a motion runtime, or ambient GPU effects.

## 3. Evidence hierarchy

When two sources disagree, use this order:

1. Security, ownership, entitlement, and preview invariants in executable code.
2. API schemas, state machines, services, and checked-in architecture documents.
3. Behavior observed in the running local interface.
4. Current official documentation for external products and browser capabilities.
5. Interpretation and design hypothesis.

Evidence labels used below:

| Label | Meaning |
| --- | --- |
| Repository evidence | Directly supported by checked-in code or an authoritative repository document |
| Direct observation | Seen in the current local product/development interface |
| External evidence | Supported by an official external product or platform source |
| Interpretation | A reasoned reading of evidence, not a product fact |
| Recommendation | The proposed OryxenAI choice |
| Unknown | Not exposed clearly enough to design as a supported capability |

## 4. Repository findings that control the design

### 4.1 Product object model

Repository evidence supports this practical hierarchy for a normal user:

```text
account
  -> one entitlement-bound portfolio session
       -> one ordered set of stage projections
       -> durable agent runs/jobs behind those projections
       -> approved artifacts
       -> at most one current production generation entitlement
       -> one active verified Preview pointer when promotion succeeds
```

This has major consequences:

- Home is not a grid of projects.
- A conversation is not the primary persistent object.
- A job is infrastructure, not a top-level destination.
- An artifact is reviewable product output, not merely a chat message.
- Preview is the trusted result of verification and promotion, not a live view of
  every source mutation.
- Normal-user successful generation becomes read-only through server policy.

The frontend should still normalize these concepts rather than bind components to
the entire JSONB session projection. Build Preparation and Code Generator continue
to evolve, so their internal field shape must not leak through the UI.

### 4.2 Actual sequence and control model

Repository evidence supports the following explicit sequence:

```text
Discover -> Content -> Design -> Prepare -> Generate -> Preview
```

Each stage is started by a separate request. Approval never silently starts the
next agent. There is no cross-agent supervisor and no supported normal-user control
for pause, cancel, steer, or queued follow-up while preparation/generation runs.

The correct UI therefore uses:

- a clear completion boundary for each stage;
- one explicit handoff action to start the next stage;
- no automatic animation that implies the next agent has begun;
- no control that the backend cannot honor; and
- no permanent chat composer during non-conversational stages.

### 4.3 Artifact behavior

Discovery, Content Architect, and Visual Design Director persist meaningful stage
outputs. Discovery is conversational; Content and Design are bounded build/revise/
approve workflows without per-stage chat. Their outputs deserve document surfaces
with sections, anchors, revision, and approval rather than large JSON blocks or a
chronological feed.

Build Preparation is different. It compiles approved upstream output, resolves
resources, materializes a disposable tree, creates and verifies a pack, and exposes
staleness. Most of those mechanics are not useful to a portfolio creator. The
product should expose semantic preparation milestones, safe warnings, whether the
handoff is eligible, and supported recovery.

Code Generator is also different. Its development harness exposes dense planning,
acquisition, verification, and diagnostic material. The production surface should
translate that into a small generation checklist and a verified result. The
development harness remains separate.

### 4.4 Preview is a security and truth boundary

Repository evidence establishes that:

- only the active promoted preview is a product Preview;
- the generated site is served from a separate opaque origin;
- unverified candidates must not be embedded;
- an unsuccessful later attempt does not erase the previous active Preview; and
- Preview is not public deployment or publishing.

Consequently, the frontend must not add a browser compiler, in-process code runner,
same-origin generated document, or optimistic candidate frame. It must validate the
Preview origin, restrict frame communication to an explicit protocol, and preserve
the old frame until a new promoted pointer is confirmed.

### 4.5 Authentication is already a state machine

The auth controller and API distinguish session restoration, sign-in, callback,
provider admission, username onboarding, unavailable/denied accounts, normal app,
and administrator access. This behavior is security-sensitive and should be
restyled, not reinvented.

The visual shell may be shared, but the auth critical path remains server-rendered
with a small self-hosted browser client. The authenticated product must not render
private session content before identity resolution.

### 4.6 Existing interfaces are evidence, not the target architecture

Direct observation found four noticeably different temporary surfaces:

- a dark, card-oriented pipeline workspace;
- a light Build Preparation diagnostic fixture;
- a dense Code Generator control room with several inspectors; and
- a beige/green authentication shell.

These surfaces prove useful behaviors such as refresh-safe state, visible progress,
Preview controls, and diagnostic separation. They do not form a coherent normal-
user experience. Reusing their product contracts is valuable; merging their visual
styles or copying developer density is not.

## 5. External product research

### 5.1 How comparisons were evaluated

For each reference product, the research asked:

- What does the product treat as the durable object?
- Where does user intent enter?
- Where do agent activity, artifacts, code, and Preview live?
- How does a long-running task communicate progress and attention?
- How are Preview and publishing separated?
- Which controls depend on backend capabilities OryxenAI does not have?
- What breaks down on smaller screens or slower devices?

Visual similarity alone was not treated as a reason to adopt a pattern.

### 5.2 Product-by-product observations

#### v0

External evidence: v0 organizes work in projects, supports prompt-driven creation,
and separates deployment operations from project work.

Useful principle:

- an application can be more durable than a single conversation;
- a generated result should have an explicit operational state; and
- deployment terminology should not be casually applied to a Preview.

Not transferable:

- OryxenAI normal users do not have a many-project workspace;
- there is no reason to reproduce v0's ecosystem-specific deployment model; and
- conversation history is not currently an OryxenAI product object.

#### Replit Agent

External evidence: Replit brings an agent, working application, checkpoints, and
deployment into one development environment.

Useful principle:

- keep the result close to the work once a visual result exists;
- tell users whether the agent is working or waiting for them; and
- distinguish development activity from deployment.

Not transferable:

- terminal, database, code, and environment controls would turn OryxenAI into an
  IDE it is not;
- checkpoints cannot be promised without a user-visible restore contract; and
- a continuously mutable development Preview conflicts with promoted-only Preview.

#### Lovable

External evidence: Lovable combines conversational changes, visual editing,
history, collaboration/visibility, and publication concepts.

Useful principle:

- artifact context and Preview should remain easy to revisit;
- review and publication are distinct decisions; and
- a user should understand what changed before making a consequential choice.

Not transferable:

- OryxenAI has no supported visual-selection/edit protocol;
- no collaboration or project visibility model exists for normal users; and
- history/rollback would be false affordances today.

#### Bolt

External evidence: Bolt keeps chat and Preview prominent while making code a
secondary technical surface.

Useful principle:

- code does not need to dominate the normal-user experience;
- Preview can become the primary surface late in the lifecycle; and
- technical detail can remain available in a separate development environment.

Not transferable:

- a permanent chat/Preview split wastes space during OryxenAI's early artifact
  stages; and
- an editable source tree is not part of the normal product contract.

#### Figma Make

External evidence: Figma Make combines prompt context, planning, an interactive
result, annotations, and a distinct publishing action.

Useful principle:

- reviewable intent before generation improves trust;
- the result should be easy to test at meaningful widths; and
- working and publishing should use unmistakably different language.

Not transferable:

- OryxenAI is not a freeform design canvas;
- design-node selection is not available as prompt context; and
- Preview cannot be annotated through the existing host protocol.

#### Google Stitch

External evidence: Stitch explores an AI-native spatial design canvas, multiple
ideas, reusable design context, and agent-driven iteration.

Useful principle:

- an AI experience need not visually center a chat transcript;
- persistent design context can be more valuable than exposing model talk; and
- spatial continuity can make agent handoffs understandable.

Not transferable:

- multiple simultaneous visual concepts are not an OryxenAI product object;
- a canvas would add interaction and rendering weight without serving the current
  ordered workflow; and
- OryxenAI cannot show unverified generation as a live design surface.

#### Rocket

External evidence: Rocket's Preview documentation includes route navigation,
responsive/device modes, fullscreen, screenshots, visual edits, staging, and
production launch concepts.

Useful principle:

- route and viewport controls solve real testing needs;
- stale/rebuilding state should be visible; and
- staging/Preview/production must not be collapsed into one word.

Transfer only the capabilities supported by OryxenAI:

- route selection from the promoted route manifest;
- mobile, tablet, desktop, and fit widths;
- refresh; and
- open in a new tab.

Do not transfer screenshot capture, visual editing, staging, or launch controls.

#### Emergent

External evidence: Emergent communicates longer-running app generation, agent
questions, visible build activity, testing, and temporary Preview behavior.

Useful principle:

- long work needs durable state, not a full-screen spinner;
- user attention must look different from background work; and
- the interface should remain useful when the person leaves and returns.

Not transferable:

- resumability, steering, or temporary candidate Preview cannot be inferred from a
  competitor; and
- detailed activity is only trustworthy when supported by OryxenAI's projection.

#### Cursor background agents

External evidence: Cursor exposes sessions for following work and supports forms
of steering/takeover in its coding environment.

Useful principle:

- current work should have a stable place;
- interruption or required input must be prominent; and
- returning users need a concise summary of what happened.

Not transferable:

- OryxenAI's production APIs do not offer takeover, pause, or live steering; and
- source diffs and terminal logs are developer details, not portfolio-creator UI.

#### GitHub Copilot coding agent

External evidence: GitHub centralizes task status, session activity, review, and
steering around repository work.

Useful principle:

- completion should lead into review rather than silently ending;
- failures need a durable, revisitable home; and
- status and user action should be visually separable.

Not transferable:

- repository-centric issue, pull-request, and review concepts do not map to the
  normal OryxenAI journey; and
- raw logs are not the correct default level of information.

### 5.3 Pattern comparison

| Design question | Common current pattern | OryxenAI decision | Why |
| --- | --- | --- | --- |
| Durable object | Project/app rather than one chat | One portfolio session | Matches entitlement and ownership |
| Primary entry | Prompt or project dashboard | Focused start/resume surface | Normal user has one portfolio |
| AI location | Persistent chat beside output | Conversation only where input is supported | Avoids false controls and wasted width |
| Progress | Activity stream plus stages | Semantic milestones plus current safe event | Backend has states but no honest percentage |
| Intermediate output | Chat blocks, documents, or tabs | Readable artifacts | Approvals require comprehension |
| Code | Visible editor or optional tab | Development harness only | Audience and product contract do not require editing |
| Preview | Persistent split or mode | Becomes dominant when verified | Preview does not exist meaningfully at every stage |
| Versioning | History/checkpoints | None in normal UI | No restore contract |
| Steering | Send while working, pause, or cancel | No controls | APIs do not support them |
| Publishing | Separate action/environment | Explicitly outside current Preview | Prevents a false production claim |
| Mobile | Reduced review/monitoring role | Start, answer, approve, monitor, Preview | A desktop IDE compressed to phone would fail |

### 5.4 Important disagreements between products

Current tools do not converge on one correct layout:

- Some keep chat permanently visible; others use modes or a canvas.
- Some expose code by default; others make it optional or invisible.
- Some show a live mutable Preview; others distinguish working, staged, and
  published results.
- Some make every action a conversation; others create durable artifacts and tasks.
- Some optimize for developers; others optimize for nontechnical creators.

The disagreement is evidence against copying a screenshot. OryxenAI should choose
from its own lifecycle: early stages are meaning and review heavy, while late stages
are result and verification heavy. A responsive, phase-changing studio fits this
better than a permanent three-column layout.

## 6. Non-AI interaction references

The proposed interface also draws on mature non-AI patterns:

### Editorial/document systems

- A readable line length, clear section hierarchy, stable anchors, and marginal
  metadata make long artifacts reviewable.
- Approval belongs near the document conclusion, not buried in a chat transcript.
- Revision comments should remain visually separate from approved source text.

### IDEs

- A stable current-task location and clear working/failure/completion states are
  valuable.
- Dense inspectors, terminals, file trees, and logs are useful only to the
  development harness, not the normal portfolio creator.

### Deployment dashboards

- Candidate, verified, promoted, and public are meaningfully different states.
- Preserve the last known-good result when a replacement fails.
- Show actionable failure summaries and keep technical references secondary.

### Workflow systems

- Ordered stages need explicit gates and current ownership.
- A system-working state must be distinct from a user-action-required state.
- Completed steps should remain inspectable without looking actionable.

### Design tools

- The artifact can become the main canvas while controls recede.
- Fixed viewport presets are more understandable and accessible than a tiny freeform
  resize handle.
- Direct manipulation should not appear until the data and security contract exists.

## 7. Visual-style evaluation

### 7.1 Selection criteria

Every style candidate was evaluated against:

1. Does it reinforce transformation from source material to portfolio?
2. Can it keep long text and decisions easy to read?
3. Can it distinguish working, attention, approval, error, and verified result?
4. Can it be implemented with HTML, CSS, small SVG, and one font subset?
5. Will it remain calm during several-minute runs?
6. Does it avoid looking like a generic AI SaaS template?
7. Can it adapt to laptop, tablet, and mobile without losing its identity?
8. Does it keep the user's generated portfolio visually separate from product
   chrome?

### 7.2 Candidate matrix

| Direction suggested | Strength for OryxenAI | Main risk | Decision |
| --- | --- | --- | --- |
| Minimalism | Fast, calm, accessible, emphasizes decisions | Can become anonymous, empty, and generic | Adopt as restraint, not as the identity |
| Maximalism | Memorable and expressive | Competes with artifacts, raises motion/asset cost, tires during long work | Reject for product shell |
| Thorium | The term is not a sufficiently clear design category from the supplied wording | Guessing could anchor the design to the wrong reference | Unresolved; do not use without a concrete reference |
| Swiss Design | Strong grid, objective hierarchy, typography, numbered sequence | Pure neutrality can feel cold | Adopt as structural discipline |
| Y2K Design | Visually recognizable and nostalgic | Novelty overwhelms trust and ages quickly | Reject |
| Editorial | Matches personal narrative, artifacts, and a portfolio becoming publishable | Can become magazine decoration if overdone | Adopt as primary identity |
| Pixel Art | Small assets can be lightweight and distinctive | Conflicts with varied professional portfolios and precise document review | Reject |
| Clay Style | Friendly and approachable | Usually asset-heavy and toy-like for approval/verification states | Reject |
| Glassmorphism (interpreting “Glass Marism”) | Can create depth with few components | Blur, transparency, contrast, GPU cost, and generic AI aesthetic | Reject |
| Cyberpunk (interpreting “Cyberpunk Part”) | Strong technical energy | Neon/dark telemetry aesthetic conflicts with author-focused trust | Reject |
| Retro collage art (interpreting “Retro College Art”) | Human, editorial, expressive | Raster assets add weight and can compete with user work | Exclude from core product; possible future campaign art only |
| Rector Art | The term is ambiguous in the supplied wording | A silent interpretation would be unreliable | Unresolved; if “vector art” was intended, the small SVG system already covers it |
| Futuristic | Can signal precision and advanced capability | Easily becomes glows, grids, and science-fiction theater | Use only as restrained technical behavior |

The interpreted entries are explicitly marked. They are not corrections to the
user's wording and should not become product requirements without confirmation.

### 7.3 Final theme decision

**Name:** Editorial Swiss — The Living Draft.

**Personality:** thoughtful, exact, quietly advanced, human before technical.

**Visual ingredients:**

- warm paper canvas;
- near-black editorial type;
- one expressive serif for large moments;
- system sans-serif for controls;
- compact monospaced annotations only for safe technical metadata;
- asymmetrical but grid-disciplined composition;
- thin rules, numbered milestones, and generous reading space;
- a single cobalt signal line;
- state colors used only for meaning; and
- a dark neutral theater only around generated Preview content.

**What makes it recognizable:** not a logo stamped on generic cards, but the same
line geometry moving through auth, journey, handoff, loading, and verified Preview.
The line starts unresolved, crosses construction points, and resolves into a browser
frame. That visual metaphor mirrors the product without pretending to show hidden
model thought.

**What it is not:**

- not beige minimalism with no point of view;
- not a magazine spread that sacrifices usability;
- not a neon agent cockpit;
- not a rounded-card dashboard;
- not a translucent glass stack;
- not a visual-design clone of any competitor; and
- not a generated portfolio theme imposed on every user's Preview.

## 8. Image and illustration strategy

### 8.1 Core decision

The normal product shell should ship **no required raster illustration**. The
interface already contains the most important visual material: the person's text,
the approved artifacts, and eventually their generated portfolio. Decorative stock
photos or AI images would add bytes while competing with that material.

Use a code-native visual system instead:

- one tiny inline SVG construction mark;
- CSS rules, typographic specimens, counters, and section geometry;
- the journey line and browser-frame motif;
- small checked-in outline SVG icons; and
- a neutral, reserved aspect-ratio frame for Preview.

This is an intentional image strategy, not an absence of design.

### 8.2 Surface-by-surface art direction

| Surface | Visual asset | Behavior | Weight/accessibility rule |
| --- | --- | --- | --- |
| Auth resolving | Construction-line mark | One short stroke travels toward a frame | Inline SVG under 4 kB; adjacent status text; static for reduced motion |
| Sign-in | Oversized type plus partial draft/frame geometry | No continuous loop | HTML/CSS/SVG only; no remote hero image |
| First portfolio | Empty editorial sheet with one starting point | Line extends after the first confirmed submission | Decorative SVG hidden from assistive tech |
| Discovery waiting | Small active segment near the current question | Does not replace transcript or status copy | Stop animation in hidden tabs |
| Artifact review | Section rules, numbering, pull-out metadata | Static | Artifact content remains primary |
| Preparation/generation | Milestone line with one active segment | Advances only on confirmed durable state | No fake percentage or endless glowing orb |
| No Preview yet | Browser-frame outline and explanatory copy | Static placeholder | Fixed aspect ratio prevents layout shift |
| Preview boot/reconnect | Existing frame retained with a local loading veil | Subtle opacity/stroke feedback | Never blank the entire studio |
| Failure | Broken line ending at the failed checkpoint | Static; recovery control is prominent | Icon plus text, never red alone |
| Completion | Line resolves into the Preview frame | One brief transition | No confetti, sound, or auto-play |

### 8.3 If raster media is introduced later

Any future marketing or onboarding raster image must satisfy all of these:

- it serves a documented communication purpose;
- AVIF/WebP is supplied with a fallback only when needed;
- responsive `srcset`, intrinsic dimensions, and lazy loading are used;
- it does not sit on the authenticated critical path;
- useful content has meaningful alternative text, while decoration uses empty alt;
- no text is baked into the image;
- the asset is checked in or served from an approved first-party origin; and
- total page weight is measured against the existing performance budget.

Generated user portfolio media stays inside the isolated Preview. It must not be
copied into the product shell or used as an unreviewed background behind controls.

## 9. Motion and “AI effect” strategy

The user requested a sense that AI affects the interface. That should come from
state-linked continuity, not decorative simulation.

### 9.1 Allowed motion grammar

- **Acknowledge:** 80-120 ms control press or focus response.
- **Reveal:** 140-180 ms opacity/translate for a newly available panel.
- **Handoff:** 220-320 ms stroke travel after a confirmed stage transition.
- **Mode change:** 180-240 ms View Transition where supported, with an immediate
  fallback.
- **Working:** one bounded SVG dash movement beside explicit status copy.
- **Completion:** the active segment settles into a static rule or frame.

All motion must animate transform, opacity, or SVG stroke properties. Layout-driven
width/height animations, continuous background gradients, blur animation, parallax,
and particle fields are prohibited.

### 9.2 State linkage

Motion may begin only from one of these facts:

- the user initiated a local control action;
- the server accepted a durable mutation;
- a normalized stage status changed;
- the active Preview pointer changed; or
- an attention state entered or cleared.

Polling ticks, elapsed-time updates, token streaming, and invented “reasoning” are
not motion triggers. Repeated polling of the same state must not replay an effect.

### 9.3 Reduced motion and hidden documents

The static composition is the base experience. Motion is progressively enabled only
under `prefers-reduced-motion: no-preference`. When a document becomes hidden, pause
waiting animation and scheduled polling. On return, refetch durable state before
animating anything. W3C technique C39 and the Page Visibility API support these
choices.

## 10. Web-platform and performance research

### 10.1 Native capabilities selected

| Capability | Evidence | OryxenAI use | Fallback |
| --- | --- | --- | --- |
| Page Visibility API | Widely available; reports visible/hidden state | Suspend scheduled polling and decorative waiting motion | Focus refetch plus capped backoff |
| BroadcastChannel | Same-origin communication across tabs/windows | Broadcast opaque state invalidation after confirmed writes | Refetch on focus/visibility |
| `content-visibility: auto` | Lets the browser skip offscreen rendering work | Long non-current artifact sections/activity groups | Normal document rendering |
| View Transitions | Provides browser-native visual continuity where available | Major in-shell posture changes only | Immediate DOM update/CSS reveal |
| Native `dialog` | Built-in modal semantics and focus behavior | Consequential confirmations | Inline confirmation region if support policy changes |
| `IntersectionObserver` | Native visibility observation | Defer secondary long artifact work | Normal lazy render |
| `postMessage` | Defined cross-window communication API | Existing versioned Preview protocol only | No host/frame feature if handshake is unavailable |

These features reduce the need for polling, motion, modal, virtualization, and
cross-tab libraries. They are progressive enhancements, not requirements for first
paint.

### 10.2 Preview messaging security

MDN's `postMessage` guidance reinforces the repository's exact-origin model:

- send to the exact expected target origin, never `*`;
- validate `event.origin` and `event.source` before reading data;
- validate the version and shape of every message;
- do not accept URLs, HTML, code, tokens, or commands outside the reviewed schema;
- remove listeners when the frame changes or the user signs out; and
- treat silence or a failed handshake as a Preview availability issue, not permission
  to weaken the origin check.

### 10.3 Long-document performance

The first implementation should not add a virtualization dependency. Instead:

- cap rendered activity to meaningful product events;
- collapse historical artifact sections while keeping headings discoverable;
- use `content-visibility: auto` and an intrinsic-size estimate for offscreen
  sections;
- parse and render safe Markdown once per artifact revision;
- reuse keyed DOM for unchanged sections;
- avoid syntax highlighting because normal users do not see source code; and
- measure before introducing a heavier solution.

### 10.4 Polling efficiency

The current contracts are polling-based. A single coordinator should:

- own one in-flight request per resource;
- poll only the active working stage;
- stop at review, complete, or needs-attention;
- suspend timers while hidden;
- refetch immediately when visible again;
- share invalidations across tabs without sharing private data; and
- apply capped exponential backoff with jitter after failures.

No component gets an independent interval. No keepalive request should be invented
to prevent a hosting provider from idling a service.

## 11. Free/low-cost hosting findings

Render is a concrete example because it was named in the request. Its official free
service documentation currently states that a free web service can spin down after
15 minutes without inbound traffic and may take about a minute to wake. It also
states that service filesystems are ephemeral, while static sites are CDN-served and
do not use the same running web-service instance model.

This separates three concerns that should not be conflated:

| Concern | Primary cause | Frontend response |
| --- | --- | --- |
| Product shell download/interaction | JS, CSS, font, image, and rendering cost | Enforce bundle and interaction budgets |
| API first-response delay | Web-service cold start or dependency latency | Preserve shell context; use “Connecting…” then a cautious “The service may be waking up” after a meaningful delay |
| Agent/build duration | Worker, model, storage, and build work | Show durable semantic milestones; allow leave-and-return |
| Preview readiness | Verified build/promotion/gateway | Retain old Preview or show a bounded Preview-specific state |

Recommendations:

- Keep the product shell small even though visual polish itself does not require
  costly infrastructure.
- Do not claim an exact wake percentage or remaining time.
- Do not fire background traffic merely to keep a free service awake.
- Do not assume an API web service can also act as a reliable always-on worker.
- Do not store portfolio or Preview data in an instance filesystem.
- Treat free hosting as development/early validation infrastructure, not a production
  reliability promise.
- If the frontend is later split into a static site, re-evaluate current same-origin
  auth/CSP/API assumptions before changing deployment topology.

## 12. Accessibility research implications

Agentic interfaces fail when every update competes for attention. OryxenAI should:

- maintain one polite status announcer for meaningful transitions;
- never announce each poll or timer update;
- move focus only after user-triggered navigation, modal action, or an inline form
  error that otherwise cannot be found;
- keep a visible current-stage label in addition to color and animation;
- expose the journey as an ordered list rather than a decorative progress bar;
- let users zoom to 200% without trapping Preview or artifact content;
- preserve keyboard access to route and viewport controls;
- provide a static equivalent for all motion; and
- test the running application with keyboard-only use and at least one desktop and
  one mobile screen reader.

The generated Preview is a separate document. The host can make its own frame and
toolbar accessible, but it cannot claim the generated site is accessible merely
because the product chrome is.

## 13. Trust, privacy, and content safety findings

### Trust

- Say “saved” only after server confirmation.
- Say “approved” only when the approved snapshot exists.
- Say “Preview ready” only when the active promoted receipt is usable.
- Say “read-only” when entitlement policy prevents further mutation.
- Distinguish a generation failure from a Preview failure.
- Preserve and label a last verified Preview when a replacement attempt fails.

### Privacy

- Do not put portfolio content, revision text, tokens, or errors in URLs.
- Do not persist full stage payloads in web storage.
- Do not send client errors or behavior analytics to a third party without a separate
  privacy decision.
- Self-host the selected font and icons.
- Ensure Preview receives no application token or account projection.

### Artifact rendering

- Render the supported Markdown subset without `innerHTML`.
- Ignore or escape raw HTML.
- Permit only reviewed `http`/`https` links and safe internal anchors.
- Add `rel="noopener noreferrer"` to new-tab external links.
- Bound artifact input and displayed activity.
- Keep a safe plain-text fallback when parsing fails.

## 14. Negative findings: what research does not justify

The investigation found no current basis for adding:

- a normal-user source editor or file tree;
- multiple projects, chats, variants, or collaborators;
- automatic stage chaining;
- user-selected models or providers;
- agent reasoning, token streams, or raw logs;
- pause, cancel, steering, or queued prompt controls;
- a fake percentage or ETA;
- element selection or screenshot-to-prompt editing;
- browser-side generated-code execution;
- Preview history or rollback;
- public publish, share, domain, or analytics controls;
- a global background-job center;
- a component kit, motion package, icon package, or client router; or
- a dark theme in the initial release.

These are not permanent bans. Each requires an actual product need and, where
appropriate, a backend/security contract before frontend affordances are designed.

## 15. Confidence and uncertainty ledger

| Finding | Confidence | Reason / next check |
| --- | --- | --- |
| One normal-user portfolio is the correct home model | High | Entitlement and session contracts support it |
| Explicit stage handoffs are required | High | No automatic chaining exists |
| Preview must show only promoted output | High | Preview architecture and service enforce it |
| Conversation is appropriate only for Discovery/revision inputs | High | Later agent APIs are bounded operations |
| Content and Design need artifact-first review | High | Approval depends on persisted structured output |
| Preact/TypeScript/Vite is the best lightweight implementation | Medium-high | Fits current complexity and budgets; validate with a production spike |
| Editorial Swiss is the correct visual identity | Medium-high | Strong product fit; requires stakeholder review and a coded specimen |
| Newsreader is the final display face | Medium | Licensing/weight fit is good; verify subset rendering across target platforms |
| Polling at the proposed cadence will be affordable | Medium | Contract supports it; measure API/DB cost under concurrent use |
| Mobile should support full authoring through approvals | Medium | User need is plausible; validate with realistic long artifacts |
| Build Preparation internal stages will remain stable | Low | Agent is evolving; adapter must tolerate change |
| Code Generator exact retry semantics will remain stable | Low | Entitlement and workflow evolution continue |
| Public publishing belongs in the same studio later | Unknown | No current product or deployment contract |
| “Thorium” or “Rector Art” names identify intended styles | Unknown | Concrete references are required before evaluation |

## 16. Questions deliberately deferred

These do not block the research recommendation, but they must be answered at the
stated gate:

- Before visual implementation: approve the Editorial Swiss direction and one coded
  token/type/motion specimen.
- Before font shipping: confirm licensed self-hosted subset files and actual WOFF2
  transfer size.
- Before production frontend rollout: choose the supported browser baseline and test
  it against the progressive fallbacks.
- Before deployment: decide whether `/app` remains FastAPI-served or static hosting
  is worth the auth/CSP/topology change.
- Before analytics or client error reporting: make a privacy and retention decision.
- Before public publishing: define ownership, deployment, failure, update, rollback,
  and sharing contracts.
- Before any direct Preview editing: define a versioned message protocol and the
  server mutation/verification loop.

## 17. Source register

### Repository sources

- `AGENTS.md`
- `DECISIONS.md`
- `docs/frontend-behavior-spec.md`
- `docs/Auth/03-user-flow-and-route-contract.md`
- `docs/code-generator-architecture/v2-production-architecture.md`
- `docs/code-generator-architecture/live-preview-and-deployment.md`
- `src/oryxenai/auth/`
- `src/oryxenai/api/routes/`
- `src/oryxenai/agents/discovery/`
- `src/oryxenai/agents/content_architect/`
- `src/oryxenai/agents/visual_design_director/`
- `src/oryxenai/agents/build_preparation/`
- `src/oryxenai/agents/code_generator/`
- `src/oryxenai/web/`

### Official external product sources

- v0 Projects: <https://api2.v0.dev/docs/projects>
- v0 Quickstart: <https://api2.v0.dev/docs/quickstart>
- v0 Deployments: <https://api2.v0.dev/docs/deployments>
- Replit Agent: <https://docs.replit.com/learn/build-with-agent>
- Replit first app: <https://docs.replit.com/build/your-first-app>
- Lovable getting started: <https://docs.lovable.dev/introduction/getting-started>
- Lovable project visibility: <https://docs.lovable.dev/features/project-visibility>
- Lovable publishing: <https://docs.lovable.dev/features/publish>
- Bolt code view: <https://support.bolt.new/building/using-bolt/code-view>
- Bolt history and restore: <https://support.bolt.new/building/using-bolt/rollback-backup>
- Figma Make creation: <https://help.figma.com/hc/en-us/articles/31304485164695-Create-a-Figma-Make-file>
- Figma Make publishing: <https://help.figma.com/hc/en-us/articles/31304586129559-Publish-update-or-unpublish-a-functional-prototype-or-web-app>
- Google Stitch update: <https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-updates/>
- Rocket mobile Preview: <https://docs.rocket.new/command-center/preview/mobile>
- Rocket launch: <https://docs.rocket.new/build/launch-web/launch-your-site>
- Emergent tutorial: <https://emergent.sh/tutorials/how-to-build-an-app-from-chatgpt-using-emergent-mcp>
- Cursor background agents: <https://docs.cursor.com/background-agent>
- GitHub Copilot agent management: <https://docs.github.com/en/copilot/concepts/agents/cloud-agent/agent-management>

### Official browser, accessibility, performance, and hosting sources

- Page Visibility API: <https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API>
- BroadcastChannel: <https://developer.mozilla.org/en-US/docs/Web/API/BroadcastChannel>
- CSS `content-visibility`: <https://developer.mozilla.org/en-US/docs/Web/CSS/content-visibility>
- `window.postMessage`: <https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage>
- View Transition API: <https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API>
- W3C reduced-motion technique C39: <https://www.w3.org/WAI/WCAG21/Techniques/css/C39>
- WAI-ARIA status technique: <https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA25>
- Core Web Vitals: <https://web.dev/articles/vitals>
- Interaction to Next Paint: <https://web.dev/articles/optimize-inp>
- Render free services: <https://render.com/docs/free>
- Render static sites: <https://render.com/docs/static-sites>
- Newsreader specimen: <https://fonts.google.com/specimen/Newsreader>

External pages change quickly. Re-check them at implementation kickoff. No external
source expands what OryxenAI's backend can safely or truthfully support.
