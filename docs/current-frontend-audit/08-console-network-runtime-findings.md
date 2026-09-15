# 08 — Console, Network & Runtime Findings

This document details the technical runtime findings observed through developer console inspection, network request tracking, and database correlation.

---

## 1. Network Activity & Polling Profile

### Request Sequence & Endpoints Observed:
```text
[Auth / App Shell]
GET /app                                      -> 200 OK (HTML Shell)
GET /static/product/assets/main-Bx8vn-iK.css  -> 200 OK (CSS Bundle)
GET /static/product/assets/main-DlRPoH9t.js   -> 200 OK (Preact Bundle)
GET /auth-static/auth-client.js               -> 200 OK (Supabase Auth Client)

[API Operations]
GET /api/v1/me                                -> 200 OK (Identity Resolution)
POST /api/v1/sessions                         -> 201 Created (New Session: 5822e80f...)
POST /api/v1/discovery/start                  -> 202 Accepted (Job Enqueued)
GET /api/v1/sessions/5822e80f...             -> 200 OK (Polled every ~2000ms)
PUT /api/v1/discovery/answers                 -> 200 OK
POST /api/v1/discovery/approve                -> 200 OK
POST /api/v1/content-architect/start          -> 202 Accepted (Job: content_architect.build)
GET /api/v1/sessions/5822e80f...             -> 200 OK (Polled)
POST /api/v1/content-architect/approve        -> 200 OK
POST /api/v1/visual-design-director/start     -> 202 Accepted (Job: visual_design_director.build)
GET /api/v1/sessions/5822e80f...             -> 200 OK (Polled)
POST /api/v1/visual-design-director/approve   -> 200 OK
POST /api/v1/build-preparation/start          -> 202 Accepted (Job: build_preparation.prepare)
GET /api/v1/sessions/5822e80f...             -> 200 OK (Polled)
POST /api/v1/sessions/5822e80f.../code-generator/start -> 202 Accepted (Job: code_generator.v5.plan)
GET /api/v1/sessions/5822e80f...             -> 200 OK (Infinite loop, ~750+ identical requests)
```

---

## 2. Critical Runtime Defect: Silent Job Failure & Infinite Polling (FE-001)

### Timeline of Failure:
1. **16:38:12 UTC (11:08:12 UTC in DB):**
   - Frontend triggers code generation via `POST /api/v1/sessions/5822e80f.../code-generator/start`.
   - Backend enqueues job `code_generator.v5.plan` (`5db62977-0bed-41ef-84ec-3f8e14491f6e`).
2. **16:39:41 UTC (11:09:41 UTC in DB):**
   - Background worker claims and executes the job.
   - Job encounters a fatal handler error.
   - Database record updated:
     - `status`: `'failed'`
     - `error_payload`: `{'code': 'HANDLER_ERROR', 'message': 'The background job handler failed.', 'retryable': False}`
     - `finished_at`: `2026-09-12 11:09:41.163240+00:00`
3. **16:39:42 to 17:04:00 (25+ minutes continuous):**
   - Frontend client executes `GET /api/v1/sessions/5822e80f-83d8-4606-b25d-05e09e92d8b8` every 2.0 seconds.
   - Response status is `200 OK`, returning:
     ```json
     {
       "session": {
         "current_stage": "generate",
         "session_status": "active"
       }
     }
     ```
   - Because the session entity itself was never transitioned to `failed` or stamped with an error event, the client-side Preact state remained frozen in `isGenerating = true`.
   - Over 750 identical HTTP requests were fired with zero backoff.
   - No user-visible error banner was rendered.

---

## 3. Console Errors & Warnings Observed

1. **Broken Image Network Failures:**
   - In Stage 04 (Build Preparation), multiple network requests for external candidate image URLs failed with network / DNS / 404 errors:
     ```text
     GET https://.../photo-151... net::ERR_NAME_NOT_RESOLVED / 404 Not Found
     ```
   - Caused by unvalidated image URLs stored in the resource catalog or external mock URLs blocked by browser environment.
2. **Right Rail State Desynchronization Warning:**
   - The right rail component (`HandoffUtility` / `AgentOutputRail`) failed to bind the active stage's JSON response from Stage 02 onwards, repeatedly logging warnings or falling back to the initial Discovery response payload.

---

## 4. Security & Content Security Policy (CSP)
- **CSP Headers Verified:**
  - `Content-Security-Policy`: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self' https://diiestlnmpaarhhexwhi.supabase.co wss://diiestlnmpaarhhexwhi.supabase.co; object-src 'none'; base-uri 'none'; form-action 'self' https://accounts.google.com; frame-ancestors 'none'`
- **Impact on Discovered Photography:**
  - The CSP specifies `img-src 'self'`.
  - In Build Preparation, the agent attempted to render external candidate image URLs (e.g. Unsplash or third-party domains).
  - The strict `img-src 'self'` CSP policy immediately blocks any external images that are not served from same-origin or explicit Supabase storage, contributing to the broken image icons!
