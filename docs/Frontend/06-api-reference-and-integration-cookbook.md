# API Reference and Integration Cookbook

> **Target Audience:** AI Coding Agents, LLM Integrators, and Automation Scripts.
> **Purpose:** Machine-readable, exhaustive API reference containing concrete HTTP contracts, header rules, exact request/response payloads, error codes, and copy-paste-ready integration recipes for all five OryxenAI stages.

---

## 1. Complete HTTP Route Master Table

All product endpoints are served under `/api/v1/`. All mutating requests (`POST`, `PUT`, `DELETE`) require a valid Bearer token from Supabase authentication.

| Endpoint | Method | Status | Required Headers | Request Payload | Response Model | Upstream Requirement |
|---|---|---|---|---|---|---|
| `/api/v1/me` | `GET` | 200 | `Authorization` | *None* | `MeProjection` | Authenticated session |
| `/api/v1/sessions` | `POST` | 201 | `Authorization` | `{ name?: string }` | `SessionResponse` | `can_create_portfolio == true` or `admin` |
| `/api/v1/sessions/{id}` | `GET` | 200 | `Authorization` | *None* | `SessionDetailResponse` | Session owner or admin |
| `/api/v1/sessions/{id}/discovery` | `GET` | 200 | `Authorization` | *None* | `DiscoveryStateResponse` | Session owner or admin |
| `/api/v1/sessions/{id}/discovery/start` | `POST` | 202 | `Authorization`, `Idempotency-Key` | `StartDiscoveryRequest` | `DiscoveryStateResponse` | Mutable session |
| `/api/v1/sessions/{id}/discovery/answers` | `PUT` | 200 | `Authorization` | `AnswersRequest` | `DiscoveryStateResponse` | Mutable session |
| `/api/v1/sessions/{id}/discovery/revise` | `POST` | 202 | `Authorization` | `ReviseRequest` | `DiscoveryStateResponse` | Status: `brief_review` |
| `/api/v1/sessions/{id}/discovery/approve` | `POST` | 200 | `Authorization` | `{}` | `DiscoveryStateResponse` | Status: `brief_review` |
| `/api/v1/sessions/{id}/discovery/stop` | `POST` | 200 | `Authorization` | `{}` | `DiscoveryStateResponse` | Status: `questions_running` or `brief_running` |
| `/api/v1/sessions/{id}/content-architect` | `GET` | 200 | `Authorization` | *None* | `ContentArchitectStateResponse` | Session owner or admin |
| `/api/v1/sessions/{id}/content-architect/start` | `POST` | 202 | `Authorization`, `Idempotency-Key` | `StartContentRequest` | `ContentArchitectStateResponse` | `discovery.status == "approved"` |
| `/api/v1/sessions/{id}/content-architect/revise` | `POST` | 202 | `Authorization` | `ReviseRequest` | `ContentArchitectStateResponse` | Status: `content_review` |
| `/api/v1/sessions/{id}/content-architect/approve` | `POST` | 200 | `Authorization` | `{}` | `ContentArchitectStateResponse` | Status: `content_review` |
| `/api/v1/sessions/{id}/content-architect/stop` | `POST` | 200 | `Authorization` | `{}` | `ContentArchitectStateResponse` | Status: `build_running` |
| `/api/v1/sessions/{id}/visual-design-director` | `GET` | 200 | `Authorization` | *None* | `VisualDesignDirectorStateResponse` | Session owner or admin |
| `/api/v1/sessions/{id}/visual-design-director/start` | `POST` | 202 | `Authorization`, `Idempotency-Key` | `StartDesignRequest` | `VisualDesignDirectorStateResponse` | `content_architect.status == "approved"` |
| `/api/v1/sessions/{id}/visual-design-director/revise` | `POST` | 202 | `Authorization` | `ReviseRequest` | `VisualDesignDirectorStateResponse` | Status: `design_review` |
| `/api/v1/sessions/{id}/visual-design-director/approve` | `POST` | 200 | `Authorization` | `{}` | `VisualDesignDirectorStateResponse` | Status: `design_review` |
| `/api/v1/sessions/{id}/visual-design-director/stop` | `POST` | 200 | `Authorization` | `{}` | `VisualDesignDirectorStateResponse` | Status: `build_running` |
| `/api/v1/sessions/{id}/build-preparation` | `GET` | 200 | `Authorization` | *None* | `BuildPreparationStateResponse` | Session owner or admin |
| `/api/v1/sessions/{id}/build-preparation/start` | `POST` | 202 | `Authorization`, `Idempotency-Key` | `StartPreparationRequest` | `BuildPreparationStateResponse` | Content & Design both `approved` |
| `/api/v1/sessions/{id}/build-preparation/regenerate` | `POST` | 202 | `Authorization`, `Idempotency-Key` | `StartPreparationRequest` | `BuildPreparationStateResponse` | Build Preparation `ready` or `stale` |
| `/api/v1/sessions/{id}/build-preparation/download` | `GET` | 200 | `Authorization` | Query: `doc=content\|visual` | Raw Markdown File | Build Preparation `ready` |
| `/api/v1/sessions/{id}/code-generator` | `GET` | 200 | `Authorization` | *None* | `CodeGeneratorStateResponse` | Session owner or admin |
| `/api/v1/sessions/{id}/code-generator/start` | `POST` | 202 | `Authorization`, `Idempotency-Key` | `{}` | `CodeGeneratorStateResponse` | `build_preparation.status == "ready"` |
| `/api/v1/sessions/{id}/code-generator/regenerate` | `POST` | 202 | `Authorization`, `Idempotency-Key` | `{}` | `CodeGeneratorStateResponse` | Mutable session |
| `/api/v1/sessions/{id}/code-generator/retry` | `POST` | 202 | `Authorization`, `Idempotency-Key` | `{}` | `CodeGeneratorStateResponse` | Code Generator `needs_attention` |

---

## 2. Exact Payload Schemas & JSON Examples

### 2.1 Identity & Session Hydration

#### `GET /api/v1/me`
**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "mayabennett",
  "role": "user",
  "status": "active",
  "onboarding_required": false,
  "admin_available": false,
  "read_only": false,
  "can_create_portfolio": false,
  "portfolio_session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f"
}
```

---

### 2.2 Stage 1: Discovery

#### `POST /api/v1/sessions/{id}/discovery/start`
**Request Headers:**
```
Content-Type: application/json
Idempotency-Key: 7b8e1a2c:discovery-start:a1b2c3d4
Authorization: Bearer <jwt>
```
**Request Body:**
```json
{
  "message": "I am a Senior End User Computing Specialist focusing on macOS/Windows fleet engineering.",
  "document_text": "PASTED RESUME CONTENT...",
  "goal": "Build a clean portfolio for senior enterprise engineering roles",
  "model_profile": "experiential_luna"
}
```
**Response (202 Accepted):**
```json
{
  "session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f",
  "session_revision": 2,
  "discovery": {
    "status": "questions_queued",
    "attempt": 1,
    "max_attempts": 3,
    "intake": {
      "message": "I am a Senior End User Computing Specialist...",
      "document_text": "PASTED RESUME CONTENT...",
      "goal": "Build a clean portfolio for senior enterprise engineering roles"
    }
  },
  "jobs": [
    {
      "id": "job-1111",
      "kind": "discovery.understand_and_question",
      "status": "queued",
      "created_at": "2026-09-09T02:00:00Z"
    }
  ]
}
```

#### `PUT /api/v1/sessions/{id}/discovery/answers`
**Request Body:**
```json
{
  "complete": false,
  "answers": [
    {
      "question_id": "primary_focus",
      "mode": "answered",
      "value": "Enterprise fleet security and automated patch orchestration"
    }
  ]
}
```

#### `POST /api/v1/sessions/{id}/discovery/approve`
**Request Body:** `{}`
**Response (200 OK):**
```json
{
  "session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f",
  "session_revision": 6,
  "discovery": {
    "status": "approved",
    "brief": {
      "title": "Maya Bennett — Portfolio Discovery Brief",
      "user_summary": "Maya is a Senior End User Computing specialist...",
      "approved": {
        "approved_at": "2026-09-09T02:05:00Z",
        "brief_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
      }
    }
  },
  "jobs": []
}
```

---

### 2.3 Stage 2: Content Architect

#### `POST /api/v1/sessions/{id}/content-architect/start`
**Request Body:**
```json
{
  "preferences": {
    "density": "moderate",
    "tone": "senior engineering leadership"
  },
  "model_profile": "experiential_luna"
}
```

#### `GET /api/v1/sessions/{id}/content-architect`
**Response (200 OK):**
```json
{
  "session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f",
  "session_revision": 9,
  "content_architect": {
    "status": "content_review",
    "user_summary": "This plan structures Maya's portfolio as a single-page architecture...",
    "site_story_strategy": {
      "positioning": "Senior End User Computing Specialist",
      "value_proposition": "Secure, manageable, dependable employee technology."
    },
    "route_plan": [
      {
        "route_id": "home",
        "path": "/",
        "title": "Maya Bennett — EUC Specialist",
        "purpose": "Introduce Maya's positioning and selected endpoint initiatives",
        "priority": "primary",
        "section_sequence": ["home:hero", "home:positioning", "home:selected-work"]
      }
    ],
    "page_content_packs": [
      {
        "route_id": "home",
        "sections": [
          {
            "section_id": "home:hero",
            "purpose": "Opening headline and core positioning statement",
            "priority": "primary",
            "content": {
              "headline": "Maya Bennett",
              "subheadline": "Senior End User Computing Specialist",
              "body": "Engineering secure, manageable employee technology at global enterprise scale."
            }
          }
        ]
      }
    ]
  },
  "jobs": []
}
```

---

### 2.4 Stage 3: Visual Design Director

#### `POST /api/v1/sessions/{id}/visual-design-director/start`
**Request Body:**
```json
{
  "preferences": {
    "visual_tone": "architectural editorial",
    "motion_preference": "restrained and purposeful"
  }
}
```

#### `GET /api/v1/sessions/{id}/visual-design-director`
**Response (200 OK):**
```json
{
  "session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f",
  "session_revision": 12,
  "visual_design_director": {
    "status": "design_review",
    "user_summary": "The visual direction establishes an architectural paper canvas...",
    "visual_language": {
      "creative_thesis": "Restrained technical craftsmanship balancing deep carbon ink with warm paper canvas.",
      "design_keywords": ["architectural", "tactile", "editorial", "precise"],
      "color_intent": "Deep carbon ink (#171a19) on warm paper (#fcfbf7) with an electric cobalt accent (#3157e7)."
    },
    "pages": [
      {
        "route_id": "home",
        "title": "Maya Bennett — EUC Specialist",
        "scenes": [
          {
            "scene_id": "home-introduction",
            "viewport_role": "Opening orientation",
            "layout_intent": "Text-dominant asymmetric composition offset by a calm technical cue.",
            "layer_stack": "Base paper surface -> Abstract line cue -> Hero headline and links",
            "relative_proportions": "2/3 text, 1/3 visual cue"
          }
        ]
      }
    ]
  },
  "jobs": []
}
```

---

### 2.5 Stage 4: Build Preparation

#### `POST /api/v1/sessions/{id}/build-preparation/start`
**Request Body:** `{}`
**Response (202 Accepted):**
```json
{
  "session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f",
  "session_revision": 15,
  "build_preparation": {
    "status": "running",
    "current_stage": "Stage 0: Deterministic scope compilation"
  },
  "jobs": [
    {
      "id": "job-3333",
      "kind": "build_preparation.prepare",
      "status": "running"
    }
  ]
}
```

#### `GET /api/v1/sessions/{id}/build-preparation`
**Response (200 OK):**
```json
{
  "session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f",
  "session_revision": 16,
  "build_preparation": {
    "status": "ready",
    "stale": false,
    "scope_hash": "84cb9c3b154af69a979f1ebec585eb3fdce15f276e5abcfa3aa9a5c99fa519bb",
    "routes": [
      {
        "route_id": "home",
        "path": "/",
        "title": "Maya Bennett — EUC Specialist",
        "purpose": "Positioning and selected initiatives",
        "section_ids": ["home:hero", "home:positioning", "home:selected-work"],
        "scene_ids": ["home-introduction", "home-selected-work"],
        "asset_ids": ["home-operating-chain", "assumed-image:home:hero:0"],
        "resource_ids": ["hero_asymmetric_text_dominant"]
      }
    ],
    "resource_index": [
      {
        "need_id": "need-photo-01",
        "role_id": "home-hero-bg",
        "category": "photo",
        "status": "candidates_found",
        "candidates": [
          {
            "provider": "unsplash",
            "url": "https://unsplash.com/photos/xyz",
            "preview_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800",
            "title": "Server rack lights",
            "attribution": "Photo by John Doe on Unsplash",
            "license": "Unsplash License"
          }
        ]
      }
    ],
    "component_index": [
      {
        "need_id": "need-comp-01",
        "role_id": "framer-motion-reveal",
        "suggestions": [
          {
            "provider": "motion/react",
            "name": "motion.div",
            "item_url": "https://motion.dev/docs/react-quick-start"
          }
        ]
      }
    ],
    "content_brief_hash": "4a5b6c7d8e9f...",
    "visual_brief_hash": "1a2b3c4d5e6f...",
    "target_contract": "react-vite-v1"
  },
  "jobs": []
}
```

---

### 2.6 Stage 5: Code Generator & Sandbox Preview

#### `POST /api/v1/sessions/{id}/code-generator/start`
**Request Body:** `{}`
**Response (202 Accepted):**
```json
{
  "session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f",
  "session_revision": 18,
  "code_generator": {
    "status": "queued",
    "current_milestone": "Queued for generation"
  },
  "jobs": [
    {
      "id": "job-4444",
      "kind": "code_generator.generate",
      "status": "queued"
    }
  ]
}
```

#### `GET /api/v1/sessions/{id}/code-generator`
**Response (200 OK — Ready with Promoted Live Preview):**
```json
{
  "session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f",
  "session_revision": 22,
  "code_generator": {
    "status": "ready",
    "stale": false,
    "current_milestone": "Portfolio generated and verified",
    "active_preview": {
      "url": "https://preview.oryxenai.local/p/7b8e1a2c-4444/",
      "candidate_id": "cand-9988",
      "build_hash": "build-a1b2c3d4e5f6",
      "route_ids": ["home"],
      "route_paths": ["/"],
      "promoted_at": "2026-09-09T02:25:00Z"
    }
  },
  "jobs": []
}
```

---

## 3. Integration Cookbook (Copy-Paste Recipes)

### 3.1 Recipe: Visibility-Aware Poller
```typescript
import { PollCoordinator } from "./data/polling";

const poller = new PollCoordinator({ intervalMs: 1500 });

// Start tracking when stage enters "working":
poller.subscribe("build_preparation", async () => {
  const response = await api.getBuildPreparation(sessionId);
  dispatch({ type: "preparation/set", view: adaptBuildPreparation(response.build_preparation) });
  if (response.build_preparation.status !== "running") {
    poller.unsubscribe("build_preparation");
  }
});
```

### 3.2 Recipe: Safe Cross-Origin Iframe Reload
```typescript
// NEVER use contentWindow.location.reload()
function reloadPreviewFrame(iframe: HTMLIFrameElement) {
  if (!iframe || !iframe.src) return;
  const current = new URL(iframe.src);
  current.searchParams.set("_reload", Date.now().toString());
  iframe.src = current.toString();
}
```

### 3.3 Recipe: Multi-Tab Broadcast Invalidation
```typescript
import { createInvalidationChannel } from "./data/invalidation";

const channel = createInvalidationChannel((msg) => {
  if (msg.sessionId === activeSessionId) {
    // Another tab advanced the portfolio, re-sync immediately:
    void refetchCurrentSession();
  }
});

// Broadcast after successful user mutation:
function notifyOtherTabs(sessionId: string) {
  channel.broadcast(sessionId);
}
```

---

## 4. Refactoring Step-by-Step Execution Checklist

AI coding agents refactoring the frontend must execute in this exact sequence:

- [ ] **Step 1: Baseline Verification:** Run `npm test` and `npm run build` in `frontend/` to ensure current clean state.
- [ ] **Step 2: Hook Decomposition:** Extract `useSessionState.ts`, `useStagePolling.ts`, `useStageMutations.ts`, and `useUrlNavigation.ts` without modifying existing DOM output.
- [ ] **Step 3: Revamp DiscoveryStudio:** Add the two-column layout rendering the `StructuredProfile` facts alongside the turn-based chat composer.
- [ ] **Step 4: Revamp ContentStudio:** Implement the interactive sitemap tree, visual section cards, and claim grounding inspector.
- [ ] **Step 5: Revamp DesignStudio:** Implement color swatches, typography scale specimen, and scene choreography wireframes.
- [ ] **Step 6: Revamp BuildPreparationHub (Fix Core Flaw):** Replace `<SafeMarkdown>` raw brief dumping with the 4-card metric dashboard, image candidate gallery, component suggestions deck, and modal brief inspector.
- [ ] **Step 7: Revamp PortfolioTheater:** Fix the cross-origin iframe reload bug, add device frames (Mobile/Tablet/Desktop/Fullscreen), and candidate preview indicator.
- [ ] **Step 8: Final Quality Gate:** Run `npm run build`, `npm run typecheck`, and `npm test`. Verify FastAPI static mount serves `.vite/manifest.json` correctly.
