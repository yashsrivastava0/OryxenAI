# OryxenAI — Change Log

Append-only record of who changed what, where, and why, so any AI tool or
Yash can reconstruct history without re-deriving it from diffs alone.

**Logging policy — log sparingly, this file must stay cheap to maintain:**

- Log **only commit-sized, "major" work**: a finished feature, a real bug
  fix, a refactor, a new file/module, an architecture or schema change —
  roughly what would earn its own git commit message. Do not log every
  individual file save or micro-edit.
- If it's unclear whether something counts as "major," **ask the user
  before adding an entry** rather than guessing — no entry is the safe
  default for anything ambiguous or clearly minor (typo fixes, formatting,
  comment wording).
- One entry per logical unit of work, not one per file touched within it.

Ordering: newest entry first, directly under "## Recent changes" below.
Never delete entries — old entries are compacted (see "Compaction
procedure" near the bottom of this file), never erased.

This file is separate from `DECISIONS.md`. Log *what happened* here; log
*open questions, rejected approaches, and deferred work* there.

## Recent changes

### 2026-08-08 19:49 UTC — Claude Code (Claude Sonnet 5 / Anthropic) — src/oryxenai/agents/visual_design_director/, src/oryxenai/db/repositories/visual_design_director.py, src/oryxenai/jobs/handlers/visual_design_director.py, src/oryxenai/api/routes/visual_design_director.py, src/oryxenai/api/dependencies.py, src/oryxenai/api/routes/__init__.py, src/oryxenai/jobs/registry.py, src/oryxenai/agents/shared/{registry,model_client}.py, src/oryxenai/core/settings.py, config/models.toml, config/app.toml, tests/, AGENTS.md, README.md, docs/architecture.md

Implemented the Visual Design Director agent (Agent 3) end to end, replacing
its static-sample mock: schemas/state machine/envelope-only validators,
a 3-stage adaptive workflow (`establish_visual_language` ->
`direct_page_experience` -> `integrate_site_experience`) mirroring Content
Architect's architecture exactly, a new deterministic local resource
catalogue (`resource_catalogue.py` + `resources/catalogue.json`, plain
Python tag-overlap lookup, never a model tool-calling loop), service/
repository/durable job handler/API routes, and a full unit/API/integration
test suite. Why: closes `DECISIONS.md` D-006 — Visual Design Director now
turns an approved Content Architect output into a session-scoped, durable,
approval-gated visual-experience direction (global visual language,
per-route storyboards, scenes, motion/interaction system, asset/resource
intent), the third pipeline stage before the still-deferred Code Generator.
No new DB table or migration was needed (JSONB on session state, same as
Discovery/Content Architect).

### 2026-08-08 16:02 UTC — Claude Code (Claude Sonnet 5 / Anthropic) — AGENTS.md, CODEX.md, CLAUDE.md, CHANGES.md, DECISIONS.md, README.md, docs/architecture.md

Restructured AI-agent context docs around a canonical `AGENTS.md` (absorbing
`CODEX.md`'s content and fixing its Content-Architect-mock contradiction),
reduced `CODEX.md` to a redirect, added `CLAUDE.md` (`@AGENTS.md` import),
and introduced this file plus `DECISIONS.md`. Why: multiple AI tools
(Claude Code, Codex CLI, Antigravity, Cursor) and models (OpenAI, xAI/Grok,
Zhipu/GLM, Anthropic) now work on this repo across devices and need one
current, non-hardcoded source of truth instead of a stale/contradictory
`CODEX.md` with no shared change history.

### 2026-08-08 (retroactive, pre-CHANGES.md history) — unspecified / unspecified — repo-wide

Recorded retroactively from `git log`, since this file didn't exist yet:
`bdc8822` initialized project scaffolding and configuration; `4e9c087`
snapshotted a v1 Discovery baseline; `d6b5b90` checkpointed a more elaborate
v2 Discovery (source-documents table, repair-prompt loop, few-shot library,
fact/conflict-graph validation) before deliberately simplifying it away (see
`DECISIONS.md` D-002); `ff291ef` completed the simplified Discovery agent
with live smoke verification; `73ac183` updated `.gitignore` for scratch/
benchmark artifacts. Agent/tool/model are unknown for this pre-changelog
period — do not guess them if extending this entry.

---

## Compaction procedure (read before appending if the file looks long)

**Trigger:** before appending a new entry, if this file is at or over
**500 lines**, compact first, in the same edit, before adding the new entry.
(500 lines keeps the file skimmable in one read — roughly 25-30 entries at
the compact 2-3 lines-plus-header the template above produces — while
giving enough headroom that compaction isn't triggered on every edit.)

**Procedure, run by whichever agent is about to append:**

1. Count entries under `## Recent changes`. Keep the most recent **20**
   entries exactly as-is — do not touch them.
2. For every entry older than the most recent 20, convert it to a single
   archive line using its own header line's date/time and summary:
   `- YYYY-MM-DD HH:MM — <Agent/Tool> (<Model/Provider>) — <area(s)> — <one-line summary>`
   (reuse the entry's existing fields; do not invent new wording).
3. Group archive lines under `## Compacted history`, in a `### YYYY-MM`
   sub-heading matching each entry's month. If a `## Compacted history`
   section and the relevant `### YYYY-MM` sub-heading already exist, append
   to them. If they don't exist yet, create `## Compacted history` once,
   above this "Compaction procedure" section and below `## Recent changes`,
   and add the needed `### YYYY-MM` sub-heading(s) under it.
4. Delete the full (now-archived) entries from `## Recent changes`, leaving
   only the most recent 20.
5. Recompute the `## Summary` block below from the full entry set (recent +
   compacted).
6. Append the new entry at the top of `## Recent changes`, per the template
   below.
7. Do not touch `DECISIONS.md` during this process — it has its own
   lifecycle and is never folded into changelog compaction.

**Entry template** (copy this block verbatim for every new entry, fill in
the fields, insert directly below the `## Recent changes` heading — i.e.
above the current newest entry):

```markdown
### YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>) — <files/areas, comma-separated>
<One or two sentences: what changed and why, combined.>
```

Field notes:

- **Agent/Tool** — the coding tool/CLI in use (e.g. `Claude Code`,
  `Codex CLI`, `Antigravity`, `Cursor`), not a person.
- **Model/Provider** — the actual underlying model and provider (e.g.
  `GPT-5.6 / OpenAI`, `Grok-4 / xAI`, `GLM-4.6 / Zhipu`,
  `Claude Sonnet 5 / Anthropic`) — never omit; this is the field most useful
  for reconstructing "why did this look different" across sessions, and it
  costs almost nothing extra since it rides in the header line.
- **Files/areas** — real paths or directories touched, not vague
  descriptions.
- The body — factual, past tense, what changed and why in one or two
  sentences combined. The header line doubles as the one-line summary used
  during compaction, so write it to stand alone.

---

## Summary (as of last compaction — 2026-08-08)

- Total entries logged: 2
- By tool: Claude Code (1), unspecified/retroactive (1)
- By model/provider: Claude Sonnet 5 / Anthropic (1), unspecified/retroactive (1)
- Last updated: 2026-08-08 16:02 UTC
