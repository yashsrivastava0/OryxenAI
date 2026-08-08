# OryxenAI — Project Context (moved)

This file used to hold OryxenAI's project context. That content now lives in
[`AGENTS.md`](AGENTS.md) at the repo root — the open cross-tool standard that
Codex CLI, Cursor, GitHub Copilot, Gemini CLI, and other AI coding assistants
read automatically by that exact filename. Keeping the real content in one
file, not two, means it can't silently drift out of sync the way this file
and `AGENTS.md` already had before this restructuring — see `DECISIONS.md`
D-007 and `CHANGES.md` for the history.

Read `AGENTS.md` for: what OryxenAI is, current implementation status,
config-driven policy (secrets vs. non-secret config, never hardcode a model
name), the repository map, worker/job semantics, canonical commands, and
where tests belong.

Other durable references:

- Developer setup and commands: [`README.md`](README.md)
- Architecture rationale ("why", not "what"): [`docs/architecture.md`](docs/architecture.md)
- Frontend/UX behavior contract: [`docs/frontend-behavior-spec.md`](docs/frontend-behavior-spec.md)
- Change history: [`CHANGES.md`](CHANGES.md)
- Decisions, open issues, and deferred work: [`DECISIONS.md`](DECISIONS.md)

This file is kept only so tools or habits that still look for `CODEX.md` by
name find a pointer instead of a dead end. Do not add project content here —
edit `AGENTS.md` instead.
