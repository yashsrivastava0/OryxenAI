# Architecture, Routing, and Auth Runtime

> **Target Audience:** AI Coding Agents, LLM Architects, and Systems Engineers.
> **Purpose:** Authoritative, exhaustive technical specification of the OryxenAI frontend architecture, build system, authentication lifecycle, URL state routing, global store, resilience coordination, and design tokens. This document is a foundational context file for the frontend revamp.

---

## 1. System Overview & Build Boundary

OryxenAI's product frontend is an authenticated single-page workspace served at `/app`. It allows users to guide their personal portfolio through five transformation stages (Discovery, Content Architecture, Visual Design Direction, Build Preparation, and Code Generation & Preview).

### 1.1 Technology Stack & Constraints

- **Framework:** Preact `10.29.8` with JSX runtime via `@preact/preset-vite`.
- **Bundler & Build Tool:** Vite `8.2.2`.
- **Language:** TypeScript `7.0.2` with strict mode (`noEmit: true` in `tsconfig.json`).
- **Styling:** Semantic Vanilla CSS with custom property tokens (`tokens.css` and `shell.css`). No CSS-in-JS, TailwindCSS, or heavyweight UI component libraries.
- **Testing:** Vitest `4.1.11` (pure Node environment for adapters, URL codec, error mapping, and resilience tests).

### 1.2 Build & Packaging Boundary

The frontend package lives in `frontend/` at the repository root. It does **not** run an independent Node server in production.

```
frontend/
├── package.json          # Defines build scripts, preact, and vite dependencies
├── tsconfig.json          # Compiler options: target ES2022, jsx: react-jsx, jsxImportSource: preact
├── vite.config.ts         # Builds to ../src/oryxenai/web/static/product/
└── src/
    ├── main.tsx           # Entry module exporting { boot, stop, restart }
    ├── app/               # AppShell, store, url-state
    ├── components/        # Reusable presentation surfaces & panels
    ├── data/              # API client, adapters, polling, errors, storage
    ├── stages/            # 5 stage controller components
    ├── styles/            # shell.css design rules
    └── test/              # Vitest test suites
```

#### Production Build Pipeline:
1. `npm run build` runs `tsc --noEmit && vite build`.
2. Vite compiles `src/main.tsx` and all imported assets into `src/oryxenai/web/static/product/`.
3. Vite writes a manifest file to `src/oryxenai/web/static/product/.vite/manifest.json`.
4. FastAPI serves the built directory as static files mounted at `/static/product/`.

#### FastAPI Integration (`src/oryxenai/web/routes.py`):
FastAPI dynamically inspects `.vite/manifest.json` on request:
```python
def _resolve_product_entry() -> dict[str, Any] | None:
    manifest_path = _STATIC_DIR / "product" / ".vite" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entry = manifest.get("src/main.tsx")
    if not isinstance(entry, dict) or "file" not in entry:
        return None
    return {
        "script": f"/static/product/{entry['file']}",
        "styles": [f"/static/product/{css}" for css in entry.get("css", [])],
    }
```

The Jinja2 template `src/oryxenai/web/templates/product_shell.html` renders:
```html
<meta name="oryxenai-product-entry" content="{{ product_entry.script }}">
{% for href in product_entry.styles %}
<link rel="stylesheet" href="{{ href }}">
{% endfor %}
<div id="product-root" aria-live="polite"></div>
<script type="module" src="/static/app-auth-bootstrap.mjs"></script>
```

---

## 2. Authentication & Bootstrap Lifecycle

The application enforces zero-trust client execution: **no protected portfolio data or model calls are executed prior to authenticated context resolution.**

### 2.1 Authentication Flow Architecture

```
Browser Requests /app
       │
       ▼
FastAPI returns product_shell.html (body.auth-pending)
       │
       ▼
/static/app-auth-bootstrap.mjs executes
       │
       ├─► Check Supabase Google Session (PKCE tokens in localStorage)
       │     └─► If no session: Redirect to /sign-in?return_to=/app
       │
       ├─► Call GET /api/v1/me with Bearer token
       │     ├─► 401 Unauthorized: Trigger token refresh -> Retry
       │     ├─► 403 Forbidden: Redirect to /access-not-approved
       │     └─► 200 OK: Returns MeProjection
       │
       ├─► Verify User Status & Onboarding:
       │     └─► If me.onboarding_required: Redirect to /onboarding
       │
       ├─► Resolve Product Entrypoint:
       │     └─► Read meta[name="oryxenai-product-entry"]
       │     └─► Dynamic import: const mod = await import(entryUrl)
       │
       └─► Boot Preact Product Shell:
             └─► mod.boot({ authorizedFetch, storage, me, role, developer, serverSessionId, readOnly })
             └─► document.body.classList.remove("auth-pending")
```

### 2.2 The `/api/v1/me` Contract

The identity projection is defined as follows:

```typescript
export interface MeProjection {
  id: string;                          // Unique user UUID (app_users.id)
  username: string | null;             // Unique handle, required before studio access
  role: "user" | "admin";              // Global role
  status: "active" | "quarantined" | "disabled";
  onboarding_required: boolean;        // True if username is null
  admin_available: boolean;            // True if user has administrative rights
  read_only?: boolean;                 // True if the user's portfolio achieved a verified preview
  can_create_portfolio?: boolean;      // Phase 3 entitlement: normal users get 1 portfolio
  portfolio_session_id?: string | null;// Active single portfolio session ID
  [key: string]: unknown;
}
```

#### Entitlement & Mutation Invariants:
1. **Single Portfolio Invariant:** Normal users (`role === "user"`) receive exactly **one** portfolio lifecycle (`me.can_create_portfolio === false` once created).
2. **Post-Success Read-Only Lock:** Once a portfolio passes Code Generator verification and promotes a live preview, `me.read_only` becomes `true`. All mutation endpoints (`POST`, `PUT`) will reject requests with `403 PORTFOLIO_READ_ONLY`. The UI disables all editing controls and switches to display/preview mode.
3. **Admin Privileges:** Users with `role === "admin"` can create multiple sessions, access `/admin`, and work with arbitrary sessions via explicit developer tools.

### 2.3 The Boot Contract Seam (`frontend/src/main.tsx`)

The Preact bundle exports three exact functions that `app-auth-bootstrap.mjs` binds to:

```typescript
export interface BootOptions {
  authorizedFetch: AuthorizedFetch;    // Fetch wrapper with auto-auth and token refresh
  storage: Storage | null;             // Safe browser storage abstraction
  me: MeProjection;                    // Current authenticated identity
  role: string;                        // "user" | "admin"
  developer: boolean;                  // Developer mode flag
  serverSessionId: string | null;      // Pre-assigned session ID (from me.portfolio_session_id)
  readOnly: boolean;                   // Read-only mutation fence flag
}

export function boot(options: BootOptions): void;
export function stop(): void;
export function restart(options: BootOptions): void;
```

When `stop()` is called (e.g. on token expiry or logout), Preact cleanly unmounts `render(null, mountedRoot)`.

---

## 3. URL State & Routing System

The studio uses search parameter-based routing instead of client-side path hashing. This ensures deep-linking and state recovery remain refresh-safe and direct.

### 3.1 Route Parameter Model (`frontend/src/app/url-state.ts`)

```typescript
export type JourneyStageId = "discover" | "content" | "design" | "prepare" | "generate";
export type ViewId = "start" | "work" | "artifact" | "progress";

export interface AppUrlState {
  stage: JourneyStageId | null;
  view: ViewId | null;
}
```

- Query parameter format: `/app?stage=<stage_id>&view=<view_id>`
- Valid stages:
  1. `discover` (Discovery Agent)
  2. `content` (Content Architect Agent)
  3. `design` (Visual Design Director Agent)
  4. `prepare` (Build Preparation Agent)
  5. `generate` (Code Generator & Live Preview Sandbox)
- Default fallback: `/app?stage=discover&view=work`

### 3.2 Upstream Gating & Safe Navigation Rules

The application prevents forward navigation into locked stages. If a user enters `?stage=generate` when Content or Design is not approved, `AppShell.tsx` evaluates completion and falls back to the earliest incomplete stage:

```typescript
let fallback: JourneyStageId | null = null;
if (requested === "content" && !discoveryApproved) fallback = "discover";
if (requested === "design" && !contentApproved) {
  fallback = discoveryApproved ? "content" : "discover";
}
if (requested === "prepare" && !designApproved) {
  fallback = contentApproved ? "design" : discoveryApproved ? "content" : "discover";
}
if (requested === "generate" && !preparationApproved) {
  fallback = designApproved ? "prepare" : contentApproved ? "design" : discoveryApproved ? "content" : "discover";
}
if (fallback) {
  selectStage(fallback, true); // replaceState
}
```

---

## 4. Global State & App Store Architecture

State in OryxenAI follows a server-authoritative pattern. The client store does **not** invent business state; it maintains normalized projections of what the PostgreSQL database has verified.

### 4.1 State Tree (`frontend/src/app/store.ts`)

```typescript
export type ConnectionState = "confirmed" | "checking" | "stale" | "offline";

export interface AppState {
  me: MeProjection | null;
  sessionId: string | null;
  sessionRevision: number | null;
  readOnly: boolean;
  activeStage: JourneyStageId;
  discovery: DiscoveryViewModel | null;
  content: ContentViewModel | null;
  design: DesignViewModel | null;
  preparation: BuildPreparationViewModel | null;
  generation: GenerationViewModel | null;
  connection: ConnectionState;
  announcement: string | null;
}
```

### 4.2 Actions & Reducer Mechanics

```typescript
export type AppAction =
  | { type: "me/set"; me: MeProjection }
  | { type: "session/set"; sessionId: string; revision: number }
  | { type: "stage/select"; stage: JourneyStageId }
  | { type: "discovery/set"; view: DiscoveryViewModel }
  | { type: "content/set"; view: ContentViewModel }
  | { type: "design/set"; view: DesignViewModel }
  | { type: "preparation/set"; view: BuildPreparationViewModel }
  | { type: "generation/set"; view: GenerationViewModel }
  | { type: "connection/set"; state: ConnectionState }
  | { type: "announce"; message: string };
```

- Context Provider: `<AppStoreContext.Provider value={{ state, dispatch }}>`
- Hook: `useAppStore()` exposes `{ state, dispatch }`.

---

## 5. Resilience, Polling & Multi-Tab Synchronization

The studio coordinates asynchronous agent background jobs through durable polling and cross-tab broadcasts.

### 5.1 Visibility-Aware Poll Coordinator (`frontend/src/data/polling.ts`)

Background jobs run on a durable PostgreSQL queue. The client tracks active jobs using `PollCoordinator`:

- **Interval:** 1,500ms default cadence during active execution.
- **Backoff on Failure:** `[1500, 3000, 6000, 12000]` ms up to a `15000` ms ceiling.
- **Visibility Detection:** Listens to `document.visibilitychange`.
  - When tab is hidden: cancels active timer, pauses polling (saves network and battery).
  - When tab returns to visible: immediately executes an out-of-band poll to catch up on state changes, then resumes standard cadence.
- **In-Flight Lock:** Guarantees only one HTTP poll is active per key at any time; never piles requests.

### 5.2 Multi-Tab State Invalidation (`frontend/src/data/invalidation.ts`)

To avoid desynchronization when a user operates in multiple tabs:
- Channel: `new BroadcastChannel("oryxenai.state-invalidated")`.
- Message format: `{ type: "state-invalidated", sessionId: string, at: number }`.
- Behavior: When Tab A submits an answer, approves a brief, or starts a stage, it posts a message to the channel. Tab B receives the event and immediately invokes `refetchCurrentSession()`.
- Security: Broadcast messages contain **only** opaque UUIDs and timestamps; never user credentials, intake text, or generated artifacts.

### 5.3 Stalled Worker Watchdog

In `ConversationSurface.tsx` and stage views, the client compares `job.created_at` and `job.heartbeat_at` against current time:
- Queued job without worker pickup for >20 seconds -> Flags worker stall notice.
- Running job without heartbeat update for >180 seconds -> Surfaces recovery options ("Worker is taking longer than expected; retry or restart").

---

## 6. API Client & Safe Error Architecture

### 6.1 Authorized HTTP Boundary (`frontend/src/data/api-client.ts`)

- Every request passes through `authorizedFetch(path, init)`.
- Automatic header injection:
  - `Content-Type: application/json`
  - `Idempotency-Key: <session_id>:<action>:<random_token>` (via `frontend/src/data/idempotency.ts`)
  - `Authorization: Bearer <supabase_jwt>`

### 6.2 Error Envelope & Sanitization (`frontend/src/data/errors.ts`)

Backend errors follow the standardized envelope:
```json
{
  "error": {
    "code": "STAGE_LOCKED",
    "message": "Content Architect requires an approved Discovery brief.",
    "details": {
      "provider_label": "Configured model provider",
      "operation_label": "plan_content",
      "retry_after_seconds": 30,
      "support_reference": "model-a1b2c3d4e5f6",
      "retryable": true
    },
    "request_id": "req-123456"
  }
}
```

The client encapsulates this in the `ApiError` class:
- Raw server stack traces, database details, and secret keys are **never** rendered.
- Provider labels are restricted to a reviewed allowlist (`"Experiential Labs"`, `"Google Gemini"`, `"Configured model provider"`).
- Known error codes map to human-friendly editorial copy in `KNOWN_MESSAGES`.

---

## 7. Design System Tokens & Aesthetics

The UI adheres strictly to the **"Editorial Swiss — The Living Draft"** design language:
- **Canvas & Warmth:** Paper-inspired backgrounds (`--canvas: #f3f0e8`, `--paper: #fcfbf7`).
- **Deep Contrast:** Carbon ink text (`--ink: #171a19`, `--graphite: #626660`).
- **Signature Accent:** Electric Cobalt Blue (`--signal: #3157e7`), used solely for confirmed actions and progress.
- **Architectural Grid:** 38px drafting grid pattern in `body::before`.
- **Typography:**
  - Display & Headings: `Newsreader`, Georgia, serif.
  - Body Text: `Segoe UI Variable Text`, `Aptos`, system-ui, sans-serif.
  - Monospace / Technical: `SFMono-Regular`, Consolas, monospace.
- **Anti-AI Slop Mandate:** No neon purple gradients, no floating glassmorphism blobs, no sparkles or magic wand emojis, and no fake circular percentage dials.
