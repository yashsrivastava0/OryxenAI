# API Reference and Integration Cookbook

> **Target Audience:** AI Coding Agents, LLM Integrators, and Automation Scripts.
> **Purpose:** Machine-readable API reference containing concrete HTTP contracts, header rules, exact request/response payloads, error codes, and integration recipes for the active Discovery and Content Architect stages.

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

## 3. Standardized Error Responses

All API errors return a uniform envelope with machine-readable codes and human-friendly messages:

```json
{
  "error": {
    "code": "PORTFOLIO_READ_ONLY",
    "message": "This portfolio has completed generation and verified preview promotion. Editing is locked.",
    "status_code": 403,
    "details": {
      "portfolio_session_id": "7b8e1a2c-9d3f-4a1e-8e7c-5a6b7c8d9e0f",
      "read_only": true
    }
  }
}
```

### Common Error Codes:
- `401 UNAUTHORIZED`: Missing, invalid, or expired Supabase Bearer token.
- `403 FORBIDDEN`: Attempt to access another user's session without admin rights.
- `403 PORTFOLIO_READ_ONLY`: Mutation attempted on a verified, finalized portfolio.
- `409 STAGE_LOCKED`: Starting stage $N$ before stage $N-1$ is approved/ready.
- `409 CONFLICT`: Optimistic concurrency check failed; session revision changed.
- `409 STALE_SOURCE`: Upstream stage re-approved after downstream started; restart required.
- `429 TOO_MANY_REQUESTS`: Rate limit or concurrency lane full.

---

## 4. Integration Cookbook (Copy-Paste Recipes)

### 4.1 Recipe: Visibility-Aware Poller

### 4.2 Recipe: Multi-Tab Broadcast Invalidation
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

## 5. Refactoring Step-by-Step Execution Checklist

AI coding agents refactoring the frontend must execute in this exact sequence:

- [ ] **Step 1: Baseline Verification:** Run `npm test` and `npm run build` in `frontend/` to ensure current clean state.
- [ ] **Step 2: Hook Decomposition:** Extract `useSessionState.ts`, `useStagePolling.ts`, `useStageMutations.ts`, and `useUrlNavigation.ts` without modifying existing DOM output.
- [ ] **Step 3: Revamp DiscoveryStudio:** Add the two-column layout rendering the `StructuredProfile` facts alongside the turn-based chat composer.
- [ ] **Step 4: Revamp ContentStudio:** Implement the interactive sitemap tree, visual section cards, and claim grounding inspector.
- [ ] **Step 5: Final Quality Gate:** Run `npm run build`, `npm run typecheck`, and `npm test`. Verify FastAPI static mount serves `.vite/manifest.json` correctly.
