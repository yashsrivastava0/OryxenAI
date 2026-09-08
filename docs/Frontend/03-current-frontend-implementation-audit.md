# Current Frontend Implementation Audit

> **Target Audience:** AI Coding Agents, LLM Refactoring Engineers, and UI Architects.
> **Purpose:** Exhaustive, line-level structural audit of the existing Preact/TypeScript frontend codebase (`frontend/src/`). Documents every component, prop interface, hook, stage controller, data adapter, utility, and test suite. Serves as the precise baseline to guide the revamp without breaking regressions or lost functionality.

---

## 1. Directory Topology

```
frontend/src/
├── app/
│   ├── AppShell.tsx            # 1,022 lines: Monolithic application orchestrator
│   ├── store.ts                # Reducer, context, and state interfaces
│   ├── store.test.ts           # Reducer transition unit tests
│   ├── url-state.ts            # Search-param query codec
│   └── url-state.test.ts       # Codec round-trip tests
├── components/
│   ├── AgentOutputRail.tsx     # Right-side drawer for copying raw stage JSON
│   ├── ArtifactSurface.tsx     # Editorial document reader (TOC + sections)
│   ├── AsyncActionButton.tsx   # Loading-aware button component
│   ├── AttentionPanel.tsx      # Error banner with retry affordances
│   ├── CacheNotice.tsx         # Cache-hit toast notification
│   ├── ClientTraceNotice.tsx   # Trace ID pill for developers
│   ├── CompletionPanel.tsx     # Milestone completion announcement
│   ├── ConnectionBanner.tsx    # Network health indicator (checking, stale, offline)
│   ├── ConversationSurface.tsx # Discovery 1-at-a-time chat composer & turn list
│   ├── ErrorBoundary.tsx       # Preact component lifecycle error boundary
│   ├── HandoffPanel.tsx        # Stage transition bridge with continue button
│   ├── JourneyRail.tsx         # Five-stage milestone progress navigation bar
│   ├── LivingDraftMark.tsx     # Animated cobalt hairline progress stroke
│   ├── ProgressSurface.tsx     # Active agent milestone progress view
│   ├── RevisionComposer.tsx    # Natural language feedback input form
│   ├── SafeMarkdown.tsx        # Zero-dependency heading extractor & markdown parser
│   ├── SafeMarkdown.test.ts    # Markdown parsing & XSS sanitization tests
│   ├── StartSurface.tsx        # Initial intake pasteboard
│   ├── StatusAnnouncer.tsx     # Screen-reader ARIA live announcer
│   └── UnsupportedPanel.tsx    # Fail-closed unrecognized status fallback
├── data/
│   ├── adapters/
│   │   ├── content.fixtures.ts
│   │   ├── content.test.ts
│   │   ├── content.ts          # Content Architect normalization
│   │   ├── design.fixtures.ts
│   │   ├── design.test.ts
│   │   ├── design.ts           # Visual Design Director normalization
│   │   ├── discovery.fixtures.ts
│   │   ├── discovery.test.ts
│   │   ├── discovery.ts        # Discovery normalization
│   │   ├── generation.fixtures.ts
│   │   ├── generation.test.ts
│   │   ├── generation.ts       # Code Generator normalization
│   │   ├── job.ts              # background_jobs row normalization
│   │   ├── preparation.fixtures.ts
│   │   ├── preparation.test.ts
│   │   ├── preparation.ts      # Build Preparation normalization
│   │   └── types.ts            # Shared StageState and StageViewModel
│   ├── api-client.ts           # Typed HTTP client wrapper around authorizedFetch
│   ├── client-diagnostics.ts   # Anonymous event logging & trace IDs
│   ├── clipboard.ts            # Safe clipboard write with fallback
│   ├── discovery-answer.ts     # Answer submission payloads
│   ├── errors.ts               # ApiError class and reviewed message catalog
│   ├── final-agent-output.ts   # Agent output serializer for copy rail
│   ├── idempotency.ts          # Idempotency-Key cache & generator
│   ├── invalidation.ts         # BroadcastChannel multi-tab sync
│   ├── polling.ts              # Visibility-aware PollCoordinator
│   └── safe-storage.ts         # Storage wrapper with memory fallback
├── stages/
│   ├── content/ContentStage.tsx
│   ├── design/DesignStage.tsx
│   ├── discovery/DiscoveryStage.tsx
│   ├── generation/GenerationStage.tsx
│   ├── preparation/BuildPreparationStage.tsx
│   └── stages.test.ts          # Cross-stage integration tests
├── styles/
│   └── shell.css               # 1,521 lines: Complete UI design system
├── test/
│   ├── accessibility.test.ts   # ARIA roles, focus management
│   ├── multi-tab.test.ts       # BroadcastChannel invalidation tests
│   ├── performance-budget.test.ts # Bundle size constraints
│   ├── product-boundary.test.ts # Entitlement & read-only enforcement
│   ├── resilience.test.ts      # Network failure & retry behavior
│   └── visual-parity.test.ts   # Token & typography verification
└── main.tsx                    # Preact entrypoint exporting { boot, stop, restart }
```

---

## 2. Deep Dive: `AppShell.tsx` (Core Application Engine)

`AppShell.tsx` is the central coordinator of the frontend studio. It manages stage transitions, session polling, optimistic mutations, error propagation, and global layout rendering.

### 2.1 Props Interface

```typescript
export interface AppShellProps {
  authorizedFetch: AuthorizedFetch;    // Auth-wrapped fetch
  me: MeProjection;                    // Current user projection
  serverSessionId: string | null;      // Pre-assigned session ID
  readOnly: boolean;                   // Post-success read-only lock
  developer?: boolean;                 // Developer tools flag
}
```

### 2.2 Internal State & Refs

- `activeStage`: Tracks currently selected `JourneyStageId` (`"discover"`, `"content"`, `"design"`, `"prepare"`, `"generate"`).
- `mutatingStage`: Holds the ID of the stage currently executing an HTTP mutation (locks UI against concurrent submissions).
- `scopedSessionKey`: Session storage key scoped to user (`oryxenai.active_session_id:${me.id}`).
- `state, dispatch`: Managed via `useReducer(appReducer, initialAppState)`.
- `pollerRef`: Persistent instance of `PollCoordinator`.
- `invalidationChannelRef`: Persistent instance of `BroadcastChannel`.
- `seenCacheReceipts`: Set tracking already-announced cache hits.
- `cacheNotice`: Active cache receipt toast data (`{ id, message }`).

### 2.3 Key Operational Handlers

1. **`refetchCurrentSession()`:**
   - Issues parallel `Promise.allSettled` requests across all 6 core endpoints:
     - `api.getSession(sessionId)`
     - `api.getDiscovery(sessionId)`
     - `api.getContentArchitect(sessionId)`
     - `api.getVisualDesignDirector(sessionId)`
     - `api.getBuildPreparation(sessionId)`
     - `api.getCodeGenerator(sessionId)`
   - Passes payloads through respective adapters (`adaptDiscovery`, `adaptContentArchitect`, etc.).
   - Executes upstream gating check: if requested stage is locked, falls back to earliest incomplete stage.
   - Updates `connection` state (`"confirmed"` if all settle, `"stale"` if any fail, `"offline"` if disconnected).

2. **Mutation Handlers:**
   - `handleStartPortfolio(notes)`: Creates session if needed, posts `/discovery/start`, enqueues questions.
   - `handleSubmitDiscoveryAnswer(answer, isComplete)`: Puts answer, triggers brief synthesis if complete.
   - `handleGenerateBrief()`: Bypasses remaining questions, enqueues brief synthesis immediately.
   - `handleApproveBrief()`: Formally approves brief.
   - `handleReviseBrief(text)`: Enqueues brief revision.
   - `runContentMutation("start" | "approve" | "revise", text?)`: Dispatches Content Architect actions.
   - `runDesignMutation("start" | "approve" | "revise", text?)`: Dispatches Visual Design Director actions.
   - `runPreparationMutation("start" | "regenerate")`: Dispatches Build Preparation actions.
   - `runGenerationMutation("start" | "regenerate")`: Dispatches Code Generator actions.

### 2.4 Layout & Presentation Structure

```tsx
<AppStoreContext.Provider value={{ state, dispatch }}>
  <a className="skip-link" href="#workspace-stage">Skip to current stage</a>
  <div className="app-shell">
    <header className="app-topbar">
      {/* Brand logo, wordmark, account monogram menu, logout */}
    </header>

    <ConnectionBanner state={state.connection} />
    <CacheNotice message={cacheNotice?.message} />
    {developer && <ClientTraceNotice traceId={getClientTraceId()} />}

    <div className="app-work-surface">
      {/* Ambient corner marks (+) and editorial margins */}
      <JourneyRail journey={journey} selectedStageId={activeStage} onSelect={selectStage} />

      <div className="app-stage-layout">
        <ErrorBoundary fallbackTitle="Unable to display this stage" onReset={refetchCurrentSession}>
          <section id="workspace-stage" className="stage-frame" data-stage={activeStage}>
            {/* Active Stage Render */}
          </section>
        </ErrorBoundary>

        {state.sessionId && <AgentOutputRail entries={outputEntries} activeStage={activeStage} />}
      </div>
    </div>

    <footer className="app-footer">
      <span>Private working space</span>
      <span>Nothing advances without approval</span>
    </footer>
    <StatusAnnouncer message={state.announcement} />
  </div>
</AppStoreContext.Provider>
```

---

## 3. Component Inventory & Functional Contract

### 3.1 `JourneyRail.tsx` (Stage Progression Rail)
- **Role:** Vertical or horizontal milestone navigation bar displaying the 5 stages.
- **Stage States Handled:**
  - `locked`: Grayed out, padlock icon, non-clickable.
  - `available`: Outlined, ready to begin.
  - `working`: Animated pulsing dot, current background worker active.
  - `input`: Awaiting user question response.
  - `review`: Artifact ready for review and revision.
  - `attention`: Warning icon, worker failed or stale upstream dependency.
  - `complete`: Solid checkmark, approved artifact locked.
- **Micro-interaction:** Renders `<LivingDraftMark active={hasActiveWork} />`.

### 3.2 `ConversationSurface.tsx` (Discovery Q&A Interface)
- **Role:** Implements the focused 1-question-at-a-time conversational interview.
- **Capabilities:**
  - `currentQuestion = questions[0]`: strictly isolates the active turn.
  - `single_select`: Renders up to 3 preset pill buttons.
  - `multi_select`: Checkbox options with multi-selection state.
  - Free-text input: Auto-expanding textarea with character feedback.
  - Autosave drafts: Keyed by `oryxenai.draft.${question.id}` in `safeSessionStorage`.
  - Skip Affordance: Submits `mode: "skipped"`.
  - "Generate brief now": Allows skipping remaining questions once minimum context exists.
  - Stalled Worker Guard: Detects `queuedAgeSeconds >= 20` or `heartbeatAgeSeconds >= 180`.

### 3.3 `ArtifactSurface.tsx` (Document Reader)
- **Role:** Standardized surface for reviewing generated Briefs, Content Architecture, and Visual Directions.
- **Features:**
  - Sticky Left Sidebar: Table of Contents (`artifact-toc`) auto-extracted from markdown headings or structured sections.
  - Status Badges: `"Approved"` vs `"Ready for review"`.
  - Warnings & Notes: Banner for omissions and caveats.
  - Two-Step Approval: "Approve" button with explicit confirmation guard.
  - Revision Trigger: Opens inline `RevisionComposer`.
  - JSON Inspector: Direct copy-to-clipboard button.

### 3.4 `ProgressSurface.tsx` (Milestone Progress Tracker)
- **Role:** Honest progress display during active agent model calls.
- **Anti-AI Slop Invariant:** Strictly **no** fake circular percentage dials or simulated progress bars.
- **Features:**
  - Discrete milestone steps (`complete`, `current`, `quiet`).
  - Elapsed seconds timer (`formatDuration(elapsedSeconds)`).
  - Explicit "Stop Agent" button to cancel durable jobs.

### 3.5 `AttentionPanel.tsx` (Error & Staleness Banner)
- **Role:** Replaces raw error stack traces with clear, actionable editorial notices.
- **Features:**
  - Safe error summary mapping.
  - Preserved work guarantee (reassures user that inputs/snapshots remain safe).
  - Retry action button (`onRetry`).
  - Collapsible `<details>` for support reference IDs (`model-xxxxxxxxxxxx`) and retry-after timers.

### 3.6 `AgentOutputRail.tsx` (Handoff Utility Drawer)
- **Role:** Collapsible `<details>` drawer on the right side of the workspace.
- **Features:**
  - Lists all 5 stages with state indicators (`Available`, `Previous result`, `Not ready`).
  - Formatted, read-only JSON textarea (`<textarea spellcheck={false} readOnly />`).
  - "Copy JSON" button with fallback to manual selection.

### 3.7 `SafeMarkdown.tsx` (Safe Parser & Headings Extractor)
- **Role:** Zero-dependency Markdown renderer and heading extractor.
- **Security:** Sanitizes raw HTML, escapes `<script>`, `<iframe>`, `javascript:`.
- **Parsing:** Handles `#`, `##`, `###`, bold (`**`), italic (`*`), unordered lists (`* `, `- `), inline code (`` ` ``), code blocks (` ``` `), and horizontal rules (`---`).

---

## 4. Stage Controllers (`frontend/src/stages/`)

| Stage Controller | File | Input Prop View | Primary User Actions |
|---|---|---|---|
| **Discovery** | `DiscoveryStage.tsx` | `DiscoveryViewModel` | Start, answer question, skip, generate brief now, approve brief, revise brief |
| **Content Architect** | `ContentStage.tsx` | `ContentViewModel` | Start, review routes/sections, revise content, approve content |
| **Visual Design** | `DesignStage.tsx` | `DesignViewModel` | Start, review thesis/scenes, revise direction, approve direction |
| **Build Preparation** | `BuildPreparationStage.tsx` | `BuildPreparationViewModel` | Prepare handoff, view briefs, regenerate handoff, download briefs |
| **Generation & Preview**| `GenerationStage.tsx` | `GenerationViewModel` | Start generation, retry, switch viewports (Mobile/Tablet/Desktop), iframe route navigation |

---

## 5. Data Adapters & Normalization (`frontend/src/data/adapters/`)

The adapters enforce a **fail-closed, defensive ingestion policy**:
1. Accept `unknown` payload.
2. Verify required envelope (`status`, `session_id`, `session_revision`).
3. If `status` is unknown or unexpected, return `state: "unsupported"` (never default to `complete` or `available`).
4. Read `latest_error` safely via `readSafeStageError`.
5. Map stage-specific background jobs from the `jobs: unknown[]` array via `selectStageJob`.

```typescript
// Shared StageState Enum
export type StageState =
  | "locked"       // Upstream stage incomplete
  | "available"    // Ready to start
  | "working"      // Background job running
  | "input"        // Awaiting user interaction (Discovery Q&A)
  | "review"       // Artifact generated, ready for approval/revision
  | "attention"    // Error or stale upstream handoff
  | "complete"     // Approved and locked
  | "unsupported"; // Unrecognized status (fail-closed)
```

---

## 6. Test Suite & Quality Gates

The `frontend/src/test/` directory contains automated verification suites ensuring behavioral invariants:
1. **`accessibility.test.ts`:** Confirms ARIA live announcements, skip links, semantic headings, and focus trap behavior.
2. **`multi-tab.test.ts`:** Simulates concurrent tabs and verifies `BroadcastChannel` invalidation triggers.
3. **`performance-budget.test.ts`:** Ensures bundle size remains within strict constraints without heavy third-party bloat.
4. **`product-boundary.test.ts`:** Validates that read-only portfolios and normal-user single-portfolio entitlements cannot be bypassed on the client.
5. **`resilience.test.ts`:** Tests network disconnects, 502/503 HTTP status responses, backoff delays, and offline recovery.
6. **`visual-parity.test.ts`:** Verifies color token names, typography variables, and layout classes.
