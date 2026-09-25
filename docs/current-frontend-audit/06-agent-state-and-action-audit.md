# 06 - Agent State & Action Audit

This document examines how Discovery and Content Architect states and user actions are represented, positioned, and synchronized in the active workflow.

## 1. Active workflow state matrix

| State | Backend job state | User-visible state | Workflow meaning |
|---|---|---|---|
| Discovery intake | No job yet | Ready to structure the brief | User can enter portfolio intent. |
| Discovery questions | `succeeded` (`discovery.understand_and_question`) | Current question and answer controls | User answers, skips, or submits questions. |
| Discovery brief review | `succeeded` (`discovery.build_or_revise_brief`) | Brief ready for review | User can revise or approve the brief. |
| Discovery approved | Session records approval | Brief approved; Content Architect is eligible to start | Approval does not start Content Architect. |
| Content Architect review | `succeeded` (`content_architect.build`) | Content plan under review | User can revise or approve the plan. |
| Content Architect approved | Session records approval | Approved content plan | Terminal state of the active workflow. |

## 2. Action placement and ergonomics

### Primary review actions

- Discovery exposes an approval action for the brief. Starting Content Architect remains a separate explicit operation.
- Content Architect approval is terminal; no further agent or stage is started.
- In the audited run, the Discovery approval action sat at y=2,850px and the Content Architect approval action sat at y=7,994px. Both were difficult to reach without long scrolling.
- The Discovery approval label wrapped across four lines in a narrow button, clipping its arrow icon (FE-013).

### Revision actions

Discovery and Content Architect review both provide revision controls. The revision action should remain visible alongside approval so users can review and revise without losing the current artifact.

## 3. Administrator action safety

During the audited creator workflow, an `ADMIN Reset Pipeline` button appeared in the top navigation. This destructive administrator action should remain in the separate, authorized `/admin` surface and its confirmation flow, not in ordinary creator navigation.