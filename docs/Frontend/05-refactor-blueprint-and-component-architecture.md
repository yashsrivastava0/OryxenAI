# Refactor Blueprint and Component Architecture

> **Target Audience:** AI Coding Agents, Frontend Engineers, and System Implementers.
> **Purpose:** Authoritative architectural blueprint for the complete revamp and refactor of the OryxenAI frontend. Outlines the target component hierarchy, state decomposition, custom hooks, stage studio designs, and CSS architecture to ensure the refactored frontend is modular, maintainable, visually stunning, and 100% compliant with backend contracts.

---

## 1. Core Revamp Philosophy & Design Principles

The revamp transforms the existing developer-heavy interface into an **executive creative studio**. It preserves all backend contracts, authentication gates, and state machine invariants while elevating the user experience.

### 1.1 Guiding Principles

1. **"Editorial Swiss — The Living Draft" Aesthetic:**
   - **Tactile Paper Canvas:** Warm paper textures and tones (`--canvas: #f3f0e8`, `--paper: #fcfbf7`), deep carbon ink (`--ink: #171a19`), and crisp hairline rules (`--rule: #d3cfc4`).
   - **Signature Electric Cobalt:** Single accent color (`--signal: #3157e7`) used solely for confirmed progress, active selections, and state transitions.
   - **The Living Draft Line:** A thin cobalt hairline connecting milestones, advancing smoothly across the screen when durable jobs complete.
   - **Strict Anti-AI Clichés:** No neon purple gradients, no floating glassmorphism blobs, no magic wand emojis, and no fake circular percentage dials.
2. **Curated Decision-Grade Visibility:**
   - Eliminate raw terminal dumps and unformatted JSON blocks from user view.
   - Present structured data (routes, visual scenes, color palettes, researched photos) using rich visual components (cards, swatches, sitemaps, galleries).
   - Retain full raw JSON inspection in an elegant, collapsible utility drawer (`AgentOutputDrawer`).
3. **Decomposed & Maintainable Reactivity:**
   - Decompose the monolithic 1,022-line `AppShell.tsx` into modular custom hooks (`useSessionState`, `useStagePolling`, `useStageMutations`, `useUrlNavigation`).
   - Ensure zero regressions in multi-tab synchronization, visibility-aware polling, and fail-closed navigation guards.

---

## 2. State & Logic Decomposition Blueprint

### 2.1 Hook Architecture

```
AppShell
  ├── useUrlNavigation()       # Manages ?stage=...&view=... and popstate
  ├── useSessionState()        # Manages session ID, revision, and /me projection
  ├── useStagePolling()        # Manages PollCoordinator & BroadcastChannel
  └── useStageMutations()      # Manages typed API mutations with Idempotency-Key
```

#### 1. `useUrlNavigation` (`frontend/src/app/hooks/useUrlNavigation.ts`)
- Encapsulates `parseAppUrlState` and `serializeAppUrlState`.
- Manages `pushState` and `replaceState`.
- Listens to browser `popstate` events.
- Exposes `{ activeStage, view, selectStage, replaceStage }`.

#### 2. `useSessionState` (`frontend/src/app/hooks/useSessionState.ts`)
- Manages `sessionId`, `sessionRevision`, `readOnly`, and `connection` status.
- Implements `refetchSession()` issuing parallel settled requests across the 6 endpoints.
- Implements upstream gating fallback logic on initial mount.
- Exposes `{ sessionId, sessionRevision, readOnly, connection, stageViews, refetchSession }`.

#### 3. `useStagePolling` (`frontend/src/app/hooks/useStagePolling.ts`)
- Instantiates `PollCoordinator` with visibility handling and backoff.
- Instantiates `createInvalidationChannel` listening to `BroadcastChannel`.
- Subscribes to active stages when their state is `"working"`.
- Pauses when tab is hidden; immediately triggers an out-of-band poll on return to visible.

#### 4. `useStageMutations` (`frontend/src/app/hooks/useStageMutations.ts`)
- Wraps all stage actions:
  - Discovery: `startDiscovery`, `submitAnswer`, `generateBriefNow`, `approveBrief`, `reviseBrief`, `stopDiscovery`.
  - Content: `startContent`, `approveContent`, `reviseContent`, `stopContent`.
  - Design: `startDesign`, `approveDesign`, `reviseDesign`, `stopDesign`.
  - Preparation: `startPreparation`, `regeneratePreparation`.
  - Generation: `startGeneration`, `regenerateGeneration`, `retryGeneration`.
- Automatically generates and caches `Idempotency-Key`.
- Manages `mutatingStage` lock to prevent duplicate submissions.
- Broadcasts invalidation events to other tabs via `BroadcastChannel`.

---

## 3. Component Hierarchy Blueprint

```
AppShell
├── StudioHeader
│   ├── BrandIdentity (Logo + "OryxenAI | portfolio editorial room")
│   ├── SessionStatusTag (Revision indicator & Read-Only badge)
│   └── AccountMenu (Monogram, user handle, admin link, sign-out)
├── ConnectionBanner (Offline / Stale / Checking indicator)
├── CacheNoticeToast (Animated toast for cached responses)
├── StudioTimeline (Revamped JourneyRail with LivingDraftMark)
├── MainWorkspaceStage (#workspace-stage)
│   ├── DiscoveryStudio        (Stage 1)
│   ├── ContentStudio          (Stage 2)
│   ├── DesignStudio           (Stage 3)
│   ├── BuildPreparationHub    (Stage 4 - Curated Command Center)
│   └── PortfolioTheater       (Stage 5 - Sandbox & Viewports)
├── AgentOutputDrawer (Collapsible right rail with formatted JSON)
└── StudioFooter (Tagline, security guarantee, keyboard hints)
```

---

## 4. Stage Studio Architectural Specifications

### 4.1 Stage 1: `DiscoveryStudio`

Replaces the basic chat list with a **two-column editorial discovery room**:

```
+------------------------------------------+------------------------------------------+
| Column A: The Interview Composer         | Column B: The Living Profile Facts       |
+------------------------------------------+------------------------------------------+
| - Current Question (large display font)  | - Live extracted profile facts:          |
| - Option Pills (max 3 preset buttons)    |   * Verified Skills tags (30+ skills)    |
| - Free-text "Something else" input       |   * Work Experience progression cards    |
| - Skip & "Generate brief now" buttons    |   * Projects & contributions             |
| - Collapsible history of answered turns  |   * Public links & credentials           |
+------------------------------------------+------------------------------------------+
```

- **Brief Review Mode:** When `status == "brief_review"` or `"approved"`, transitions to a split brief reader:
  - Left: `brief.user_summary` and structured profile snapshot.
  - Right: Full brief markdown reader with sticky table of contents.
  - Footer toolbar: "Approve brief" with confirmation modal and "Request revisions" composer.

---

### 4.2 Stage 2: `ContentStudio`

Replaces flattened markdown bullets with an **interactive content and route architecture**:

```
+-------------------------------------------------------------------------------------+
| Strategic Positioning Card: Title, Value Proposition, Audience, Primary Call to Action |
+-------------------------------------------------------------------------------------+
| Visual Route Map (Interactive Sitemap):                                             |
| [ / (Home) ] ---------> [ /work (Selected Work) ] ---------> [ /about (About Maya) ]  |
+-------------------------------------------------------------------------------------+
| Section Architecture Deck (Route-by-Route):                                         |
| +-------------------------+ +-------------------------+ +-------------------------+ |
| | Section: home:hero      | | Section: home:position  | | Section: home:work      | |
| | Priority: Primary       | | Priority: Standard      | | Priority: Standard      | |
| | Headline & Subhead      | | Narrative Body copy     | | 3 Feature initiatives   | |
| | Grounded Claims: 2      | | Grounded Claims: 1      | | Grounded Claims: 4      | |
| +-------------------------+ +-------------------------+ +-------------------------+ |
+-------------------------------------------------------------------------------------+
| Collapsible Drawer: Claim Grounding Ledger (Verified, Team Ownership, Publication)  |
+-------------------------------------------------------------------------------------+
```

- **Features:**
  - Route navigation tabs: Switching routes displays that route’s sections.
  - Section wireframe cards: Renders actual headlines, subheadlines, narrative paragraphs, and tag lists.
  - Decision Basis Drawer: Displays provenance records (`decision`, `value`, `basis`, `rationale`).

---

### 4.3 Stage 3: `DesignStudio`

Transforms the text-only design direction into an **aesthetic moodboard and design system viewer**:

```
+-------------------------------------------------------------------------------------+
| Creative Thesis Card: Aesthetic Philosophy & Design Keywords                        |
+-------------------------------------------------------------------------------------+
| Color Palette Swatches:                                                             |
| [ #fcfbf7 Canvas ] [ #171a19 Ink ] [ #3157e7 Signal ] [ #626660 Graphite ] [ Accent ]|
+-------------------------------------------------------------------------------------+
| Typographic Hierarchy Specimen:                                                     |
| Display: "Maya Bennett" (Newsreader 56px)                                            |
| H1: "Senior End User Computing Specialist" (Newsreader 36px)                         |
| Body: "Secure, manageable, dependable employee technology." (Aptos 16px)            |
| Monospace: "home:hero / scene-01" (SFMono 12px)                                     |
+-------------------------------------------------------------------------------------+
| Scene Choreography Blueprint:                                                       |
| Card per scene showing:                                                             |
| - Layout Intent (Asymmetry, alignment rails)                                        |
| - Layer Stack (Z-index order & depth planes)                                        |
| - Motion & Reveal Behavior (Trigger, duration character)                            |
| - Responsive & Reduced Motion Rules                                                 |
+-------------------------------------------------------------------------------------+
| Catalogue Resource Patterns:                                                        |
| Visual cards showing adapted patterns (e.g. hero_asymmetric_text_dominant)           |
+-------------------------------------------------------------------------------------+
```

---

### 4.4 Stage 4: `BuildPreparationHub` (Fixing the Core Problem)

Completely replaces the raw markdown text dump with a **curated build command center**:

```
+-------------------------------------------------------------------------------------+
| Header Summary Metrics:                                                             |
| [ 4 Routes Bound ]    [ 40 Resource Needs ]    [ 23 Discovered Assets ] [ 13 Components ]|
+-------------------------------------------------------------------------------------+
| Researched Photography & Asset Gallery:                                             |
| Grid of discovered candidates from Unsplash / Wikimedia:                            |
| +--------------------+ +--------------------+ +--------------------+                |
| | [ Image Thumbnail] | | [ Image Thumbnail] | | [ Image Thumbnail] |                |
| | Title & Provider   | | Title & Provider   | | Title & Provider   |                |
| | License & Credit   | | License & Credit   | | License & Credit   |                |
| | Bound: home:hero   | | Bound: home:work   | | Bound: about:team  |                |
| +--------------------+ +--------------------+ +--------------------+                |
+-------------------------------------------------------------------------------------+
| Component Pattern Suggestions Deck:                                                 |
| Cards showing researched components (Framer Motion, headless disclosures, etc.)     |
+-------------------------------------------------------------------------------------+
| Route Scope Index:                                                                  |
| Hierarchical tree: Route -> Section Sequence -> Bound Scenes -> Asset IDs           |
+-------------------------------------------------------------------------------------+
| Technical Handshake Toolbar:                                                        |
| [ Inspect Content Brief (Modal) ]  [ Inspect Visual Brief (Modal) ]  [ Download Briefs ]|
+-------------------------------------------------------------------------------------+
```

#### Brief Modal Specification:
When the user clicks "Inspect Content Brief" or "Inspect Visual Brief":
- Opens an elegant reader modal with syntax highlighting.
- The machine-readable fenced JSON block (````json build-preparation-content-index ... ````) is **parsed and rendered as an interactive property inspector**, not a giant block of raw text.
- The remaining Markdown prose is formatted cleanly with typography tokens and a table of contents.

---

### 4.5 Stage 5: `PortfolioTheater` (Sandbox & Live Preview)

Upgrades the basic preview iframe into an **interactive device theater**:

```
+-------------------------------------------------------------------------------------+
| Device Theater Toolbar:                                                             |
| Route Selector: [ / (Home) ▾ ]                                                      |
| Viewport Switcher: [ Mobile 390px ] [ Tablet 768px ] [ Desktop 1440px ] [ Fit 100% ]|
| Mode: [ Verified Success 🟢 ] or [ Candidate Preview 🟡 (Unverified) ]              |
| Actions: [ ⟳ Refresh Preview ] [ ↗ Open in New Tab ] [ ⛶ Fullscreen Theater ]        |
+-------------------------------------------------------------------------------------+
| Sandbox Frame Container:                                                            |
| +---------------------------------------------------------------------------------+ |
| |                                                                                 | |
| |   [ Interactive Embedded Portfolio Sandbox (iframe) ]                           | |
| |                                                                                 | |
| +---------------------------------------------------------------------------------+ |
+-------------------------------------------------------------------------------------+
```

#### Safe Cross-Origin Reload Implementation:
```typescript
// NEVER call frame.contentWindow.location.reload() (causes cross-origin SecurityError)
// ALWAYS reassign src or remount:
const handleRefresh = () => {
  if (!frameRef.current) return;
  const currentUrl = new URL(frameRef.current.src);
  currentUrl.searchParams.set("_t", Date.now().toString());
  frameRef.current.src = currentUrl.toString();
};
```

#### Candidate Preview Findings Banner:
When `candidate_preview` is present without verified promotion:
- Displays an amber attention banner: *"Candidate preview generated. Some checks need attention before final promotion."*
- Lists non-blocking warnings and geometry check results.
- Provides an explicit "Retry Verification" action.

---

## 5. CSS Architecture & Token Integration

### 5.1 Stylesheet Organization

```
frontend/src/styles/
├── tokens.css             # Colors, typography scales, spacing, radii, timing
├── base.css               # Reset, paper canvas background, 38px drafting grid
├── layout.css             # AppShell grid, topbar, footer, stage container
├── timeline.css           # Studio timeline and LivingDraftMark stroke
├── components/
│   ├── buttons.css        # Primary, secondary, quiet, async buttons
│   ├── cards.css          # Paper cards, elevated glass surfaces
│   ├── drawers.css        # AgentOutputDrawer, details popovers
│   └── modals.css         # Brief inspector modals and dialogs
└── stages/
    ├── discovery.css      # Q&A composer, profile cards
    ├── content.css        # Sitemap tree, section wireframe cards
    ├── design.css         # Palette swatches, type specimens, scene cards
    ├── preparation.css    # Asset gallery, command center metrics
    └── preview.css        # Device theater frames, viewport transitions
```

### 5.2 Token Usage Standards

| Purpose | Token Variable | Value |
|---|---|---|
| Background Canvas | `var(--canvas)` | `#f3f0e8` |
| Paper Card Surface | `var(--paper)` | `#fcfbf7` |
| Elevated Paper Surface | `var(--paper-elevated)` | `#ffffff` |
| Primary Ink Text | `var(--ink)` | `#171a19` |
| Secondary Ink Text | `var(--ink-secondary)` | `#353936` |
| Graphite / Meta Text | `var(--graphite)` | `#626660` |
| Hairline Rules & Borders | `var(--rule)` | `#d3cfc4` |
| Active / Focus Rule | `var(--rule-focus)` | `#3157e7` |
| Electric Cobalt Accent | `var(--signal)` | `#3157e7` |
| Display Typography | `var(--font-display)` | `"Newsreader", Georgia, serif` |
| Body Typography | `var(--font-body)` | `"Segoe UI Variable Text", "Aptos", sans-serif` |
| Monospace Typography | `var(--font-mono)` | `"SFMono-Regular", Consolas, monospace` |
