# Discovery Agent

Discovery is the first active OryxenAI workflow. It reads the user's portfolio
goal and supplied text, preserves addressable source spans, asks adaptive
clarification rounds when they can materially improve the result, and produces
a reviewable Discovery Brief plus a source-linked `DiscoveryDossier/v1`.
Discovery stops after explicit approval. Content Architect remains a separate,
explicitly started stage.

## Responsibilities

- Preserve intake text and user answers in session state, including source
  document digests and UTF-16 offsets that map directly to browser selections.
- Distinguish personal facts, user intent/preferences, team scope, job criteria,
  references, duplicates, exclusions, conflicts, and explicit restrictions.
- Ask zero to three focused questions in one contextual batch. Ask none when
  the supplied context is sufficient. Users can skip individual questions;
  each answer is saved before the next question appears. The interview does
  not repeat after the batch is complete.
- Produce a detailed editable brief and a dossier whose facts, entities,
  restrictions, open items, and source coverage reference the supplied spans.
- Require explicit approval of the current brief and dossier snapshot.

## Non-responsibilities

Discovery does not write final public website copy, fetch links, analyze binary
documents or images, or start another agent. Text supplied by the user remains
the evidence boundary. Intake attachments and OCR can be added as a separate
deterministic Intake capability later.

## Flow

1. `POST /api/v1/sessions/{id}/discovery/start` stores the text and creates
   immutable source-document snapshots. `source_text`, `message`, and
   `document_text` are addressable source material; `goal` is recorded as user
   intent. New text can be appended after `NEEDS_INPUT` without discarding
   earlier material.
2. The worker runs `understand_and_question`. It returns `NEEDS_DETAILS`,
   `ASK_QUESTIONS`, or `READY_FOR_BRIEF`; question batches contain at most
   three questions. User answers and skips are persisted with their history
   and answer-source spans.
3. Submitting the final answer or skip queues brief preparation immediately.
   `continue_with_current_information` remains an API-compatible way to end
   a partial batch. In the product UI, `READY_FOR_BRIEF` automatically queues
   the brief. Discovery still waits for explicit approval before Content
   Architect can start.
4. `POST .../discovery/revise` regenerates the brief and dossier from the same
   source snapshots, answers, and revision request.
5. The review surface presents the report alongside an evidence inspector for
   source excerpts, claim references, source coverage, open items, restrictions,
   and question history.
6. `POST .../discovery/approve` hashes the reviewed Markdown and dossier
   together. Content Architect snapshots the full approved dossier, retaining
   the compact profile as a compatibility aid for older approved sessions.

## Source and dossier contracts

Source documents live in the existing Discovery JSONB session snapshot; no
database migration is required. Each document preserves the exact original
text, its SHA-256 digest, a label, and non-overlapping spans. Offsets count
UTF-16 code units so browser `String.slice` can select the same excerpt.
Answer text is indexed as a source document. Skips and unanswered questions
remain explicit history events, not evidence.

`DiscoveryDossier/v1` contains intent, subject, source-linked facts, roles,
projects, other evidence, open items, restrictions, one disposition per source
span, question history, and server-owned lineage metadata. Validation rejects
duplicate or missing coverage, unknown references, ungrounded facts, broken
fact links, and lineage that does not match the supplied source snapshot. The
legacy `StructuredProfile` used by Content Architect is rebuilt from the
dossier, with no project truncation. Existing sessions without source snapshots
are marked unverified; they are not retroactively presented as source-linked.

The approval hash includes both `brief_markdown` and the dossier snapshot, so a
source or claim change invalidates downstream approval matching.

## State machine

Statuses include `not_started`, `questions_queued`, `questions_running`,
`needs_input`, `questions_ready`, `answers_in_progress`, `brief_running`,
`brief_review`, `approved`, and `needs_attention`. A completed answer batch
proceeds to `brief_running`; `READY_FOR_BRIEF` skips questions entirely. A
nonterminal operation can fail into `needs_attention`. Eligible pre-send
failures can follow the worker retry policy. When a
provider error has used the run's call allowance, Discovery shows the
original provider or output failure and offers an explicit stage retry with
the saved intake and answers.

## Prompt and model configuration

The shared and operation prompts define the evidence hierarchy, anti-injection
boundary, adaptive interview method, dossier coverage rules, and report
quality. Prompt versions and module hashes invalidate stale structured-result
cache entries. Provider, model profile, operation context ceiling, output
budget, and fallback policy remain in `config/models.toml`; question batch size
is configured in `config/app.toml`. No model name is frozen in this document.

## HTTP surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/sessions/{id}/discovery` | Current state, dossier, sources, jobs, and safe errors |
| POST | `/api/v1/sessions/{id}/discovery/start` | Store or append intake and queue question analysis |
| PUT | `/api/v1/sessions/{id}/discovery/answers` | Save answers; optionally continue with current information |
| POST | `/api/v1/sessions/{id}/discovery/revise` | Revise the brief and dossier while under review |
| POST | `/api/v1/sessions/{id}/discovery/approve` | Approve the current brief and dossier snapshot |
| POST | `/api/v1/sessions/{id}/discovery/stop` | Stop active work while preserving source and answer history |
