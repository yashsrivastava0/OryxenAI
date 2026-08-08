@AGENTS.md

## Claude Code notes

Everything above this line is imported from `AGENTS.md`, the canonical,
cross-tool project context shared by every AI tool working on this repo. Do
not duplicate project facts here — add only notes specific to Claude Code
itself.

- **Session memory is local and Claude-only.** Claude Code keeps its own
  per-project memory under `~/.claude/projects/<project-hash>/memory/` on
  each machine. It is not shared with other AI tools (Codex CLI, Antigravity,
  Cursor) and not synced across devices, and it is not a substitute for
  `CHANGES.md`/`DECISIONS.md`. Anything another agent, or a future session on
  another device, needs to know belongs in those files, not only in memory.
- **Before non-trivial work:** check `DECISIONS.md` for prior decisions or
  rejected approaches, then follow `AGENTS.md`'s multi-agent collaboration
  protocol — log commit-sized work to `CHANGES.md` afterward (running its
  compaction check), and ask before logging anything ambiguous rather than
  guessing.
