# Content Architect Agent

Content Architect is the second OryxenAI workflow stage. It
converts an **approved** Discovery result into the complete, grounded,
person-specific copy for a **single-page portfolio**. Its output is reviewed
and approved by the user, then Code Generator writes `index.html` against the
selected, immutable theme package. This agent
never writes HTML or CSS.

## Responsibilities

- Decide positioning, the story the page tells, and the primary visitor action.
- Write every visitor-facing field of the page content tree (below), final
  and plain text, sized for the template's slots.
- Carry claim-level grounding (source, evidence status, individual vs team
  ownership, publication status) and bind each approved claim to the exact
  page fields that rely on it.
- Record one disposition for every dossier fact, role, project, and other
  evidence item (`used`, `condensed`, `retained_internally`,
  `excluded_by_restriction`, `excluded_editorially`, `unresolved`).
- Record why major content decisions (audience, CTA, tone, density) were made.
- Stop after producing content; never invoke another agent.

## Non-responsibilities

Content Architect must NOT re-interview the user, change approved Discovery
facts, invent employers, dates, metrics, awards, testimonials, links, or
outcomes, generate HTML/CSS/React/SVG, or research anything outside the
snapshot.

## Input: the approved Discovery dossier

A snapshot of the approved `DiscoveryDossier/v1` (all source-linked facts,
entities, restrictions, question history, open items), plus the brief title,
summary, structured profile, selected theme id, approval hash, and session revision. The raw
pasted text and Markdown brief stay upstream. The raw `styles.css` is **not**
sent: the template's slots, counts, and length limits are written into
`prompts/system.md` (`<page_template>`) instead.
For model calls with a complete dossier, the duplicate structured profile is
omitted from the prompt packet; older profile-only sessions retain it. The
schema prompt is compact JSON to reduce repeated input without changing its
requirements.

## The page content tree (`PortfolioPageContent`)

One typed object whose regions mirror the pinned template one-to-one
(`schemas.py`; vocabulary shared with the frontend adapter):

| Region | Fields |
| --- | --- |
| `hero` | `name`, `eyebrow_primary`, `eyebrow_secondary`, `headline_prefix`, `headline_emphasis`, `intro`, `location`, `primary_cta_label`, `secondary_cta_label` |
| `metadata` | `title`, `description` |
| `marquee_keywords` | decorative keyword ticker (one list; duplicated into the DOM by the template consumer) |
| `systems_practice` | `eyebrow` (also the nav label), `heading`, `intro`, **exactly 4** `pillars` (`title`, `description`) |
| `technical_capabilities` | `eyebrow`, `heading`, `intro`, `groups[]` (`heading`, `items[]`) |
| `professional_context` | `eyebrow`, `heading`, `intro`, `organizations[]` — **names only** (the template has no slot for roles or dates) |
| `connect` | `eyebrow`, `heading`, `intro`, `destinations[]` (`label`, `url`, `featured`) |
| `atlas` | Cobalt Atlas v2 only: About heading/intro/optional quote, grounded experience, education, statistics, and up to three projects. |

Deliberately not modeled: hrefs other than `connect.destinations[].url`
(nav and hero CTAs use template-fixed anchors), numeric indexes, the
`preview` line of a capability group, and the monogram — the template consumer
derives those from the fields above so they can never drift. The template has
no projects, experience, education, or metrics section in the three CSS-only
themes; that material is folded into pillars, the hero intro, and capability
groups. Cobalt Atlas v2 adds the `atlas` supplement while retaining the common
tree. Optional rows are omitted when source facts are missing. An illustrative
concept requires the owner's explicit Discovery opt-in and a visible label.

Model output extras are dropped (`extra="ignore"`) instead of failing a
finished run; internal-review key leakage is still rejected.

## The adaptive bounded workflow

One durable job (`content_architect.build`); its agent makes up to three
sequential model calls, never one per section:

1. **`plan_content`** (always) — story strategy and claim grounding, and
   either the FULL page content in the same call (`content_included=true`) or
   a deferral (`content_included=false`) when the dossier is too rich.
2. **`write_pages`** (only if deferred) — the complete page content tree,
   refreshed claim `field_paths`, and the full coverage ledger.
3. **`integrate_content`** (only if the writer flagged inconsistency, or as
   the single bounded repair pass when the deterministic readiness check finds
   a defect and call budget remains) — never adds a claim or promotes a
   publication status.

All three share one output contract, `ContentArchitectOutput`, discriminated
by `mode`. After the last call, `agent.py::_approval_readiness_errors` runs
the same checks approval will later enforce; unrepaired defects fail the run
(`MODEL_OUTPUT_INVALID`) rather than reaching review.

## Flow

1. `POST /api/v1/sessions/{id}/content-architect/start` requires Discovery
   `approved`, snapshots the dossier and approval hash, enqueues the build.
2. The worker runs the build and moves the state to `content_review`.
3. `POST .../revise` re-runs the build with a natural-language
   `revision_request` and the current content as `prior_output`.
4. `POST .../approve` re-checks Discovery staleness, page completeness,
   claim binding, and dossier coverage, hashes the content, and marks the run
   `approved` (terminal).

## Rules enforced in code (`page_content.py`)

Pure functions over plain dicts, shared by the validators, the agent's
readiness gate, the state machine, and the service:

- **Shape** (`validators.py`, per model call): wrong JSON types, internal-review
  key names (`status_note`, `evidence_status`, `publication_check`, ...) inside
  page copy, and a `blocked` claim bound to any field are hard rejects — both
  were observed leaking through in real live-model output despite prompt
  instructions.
- **Completeness** (readiness gate + approval): hero name/headline/intro,
  metadata title/description, section eyebrow+heading, **exactly four
  pillars** each with title and description, at least one capability group
  with items, and `https://`/`http://`/`mailto:` destination URLs.
  Organizations, destinations, and marquee keywords may be empty — an invented
  entry is worse than an empty list. Completeness is repairable by the one
  bounded `integrate_content` call, which is why it is not a per-call
  validator.
- **Claim binding**: `claim_grounding[].field_paths` uses dotted/bracket paths
  (`hero.intro`, `systems_practice.pillars[0].description`,
  `connect.destinations[1].label`). An `approved` claim's paths must point at
  populated copy; a `pending` or `blocked` claim has no paths.
- **Coverage**: for a dossier-backed run, every fact/role/project/evidence id
  (`fact/<id>`, `role/<id>`, ...) has exactly one ledger entry with a valid
  disposition. `used`/`condensed` entries carry populated `field_paths`; every
  other disposition carries a reason and no paths.

`evidence_status`, `ownership`, and `publication_status` stay three
independent fields on each claim. An approved Discovery snapshot authorizes
neutral, factual wording for ordinary supplied facts; missing metrics or
unclear ownership are reasons to omit or generalize a detail, not to block the
page. Explicit privacy, NDA, or do-not-publish restrictions remain blocking.

## Staleness

Every `start`/`revise`/`approve` call — and the job handler again immediately
before persisting a successful build — compares the live Discovery approval
hash with the snapshot. A mismatch is rejected with
`CONTENT_ARCHITECT_STALE_SOURCE`.

## State machine

Five statuses: `not_started, build_running, content_review, approved,
needs_attention`. One job kind covers the whole adaptive workflow, so there is
no per-stage status (an intentional simplification; see `state.py`).

Approval error codes: `CONTENT_ARCHITECT_PAGE_NOT_PUBLISHABLE` (no page
content), `CONTENT_ARCHITECT_PUBLIC_SCOPE_INCOMPLETE` (incomplete or unsafe
page), `CONTENT_ARCHITECT_COVERAGE_INCOMPLETE`,
`CONTENT_ARCHITECT_STALE_SOURCE`, `CONTENT_ARCHITECT_DISCOVERY_NOT_APPROVED`.
Sessions saved with the earlier route-based schema still load but show an empty
page; run Content Architect again for them.

## Prompts

`prompts/system.md` (shared, carries the page template, claim-binding, and
coverage rules — only one operation file loads per call, so a rule a validator
enforces must live here or in that operation file, never as a cross-reference),
then `plan_content.md`, `write_pages.md`, `integrate_content.md`, each with the
shared JSON schema injected and the source packet appended as untrusted data.
`samples/` holds three input/output pairs (strong, sparse, NDA-restricted);
`tests/unit/agents/content_architect/test_samples.py` keeps them valid.

## Model integration

Provider, model, and routing come from `config/models.toml`:
`[routing.engine_profiles]` and the per-operation
`[routing.operation_profiles.content_architect.*]` entries resolve the live
profile (the same single provider as Discovery). The static
`[profiles.content_architect]` block is not consulted for live routing while
those entries exist. The mock-runs dev harness uses the deterministic
`MockModelClient`, so it never makes network calls.

## HTTP surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/sessions/{id}/content-architect` | Current state (status, error, attempt, elapsed) |
| POST | `/api/v1/sessions/{id}/content-architect/start` | Snapshot approved Discovery, enqueue build (202) |
| POST | `/api/v1/sessions/{id}/content-architect/revise` | Natural-language content revision (202) |
| POST | `/api/v1/sessions/{id}/content-architect/approve` | Approve the reviewed content |
| POST | `/api/v1/sessions/{id}/content-architect/stop` | Cancel the running build |
