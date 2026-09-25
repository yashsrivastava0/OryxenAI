# 10 - Journey & Information Architecture Findings

This document summarizes information architecture and usability findings from the audited Discovery and Content Architect workflow.

## 1. Result representation

Discovery presents a portfolio brief and profile facts for review. Content Architect presents a content plan with a narrative thesis, routes, sections, and copy. The current layouts make these artifacts difficult to scan because long prose and raw metadata compete for attention.

## 2. Vertical expansion and review actions

- The Discovery approval action was 2,850 pixels below the top of the brief.
- The Content Architect approval action was 7,994 pixels below the top of the content plan.
- Sticky, reserved action controls and a summary-first review can keep decisions reachable while the user reads.
- Content Architect approval is the terminal state of the active workflow.

## 3. Layout collisions and column width

- The Content Architect status badge overlapped the H1 title (FE-002).
- Content sections occupied a narrow column while substantial canvas width remained unused (FE-007).

## 4. Developer tooling and administrator controls

- The `HANDOFF UTILITY` rail exposed raw JSON in the ordinary creator workspace (FE-009). Keep inspection tools closed by default and separate from normal review.
- An `ADMIN Reset Pipeline` control appeared in the creator header. Destructive administrator actions belong in the authorized `/admin` surface with confirmation.

## Summary of journey clarity

| Question | Observed finding |
|---|---|
| Where am I? | The active Discovery or Content Architect state should remain visually clear, including during questions and review. |
| What has happened? | The approved Discovery brief and Content Architect plan should remain distinguishable in the session history. |
| What is happening now? | Working states need a clear status and should stop polling when the job reaches a terminal result. |
| What did the agent produce? | Discovery produces a brief; Content Architect produces a reviewable content plan. |
| What requires my judgment? | Discovery brief approval and Content Architect plan approval are the two review decisions; the latter ends the active workflow. |