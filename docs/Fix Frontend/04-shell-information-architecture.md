# Replacement shell and information architecture

## Shell anatomy

The creator experience uses one primary reading surface:

```text
┌──────────────────────────────────────────────────────────────┐
│ brand / portfolio status                         account      │
├──────────────────────────────────────────────────────────────┤
│ compact stage navigator: Discover · Content · Design · ...   │
├──────────────────────────────────────────────────────────────┤
│ stage context strip: stage label · state · 2–4 useful facts  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                  primary stage canvas                        │
│          artifact, route map, scenes, preview, etc.           │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ sticky reserved ActionDock: primary / secondary / status      │
└──────────────────────────────────────────────────────────────┘
```

The developer-only Output Inspector is a slide-over/drawer opened from a quiet utility action. It does not consume permanent layout width and is closed by default.

## Topbar

Keep the brand and account menu. Reduce the descriptor to a quiet sentence-case label. Remove decorative or administrative controls from the creator's primary action area. Admin reset remains available in the admin/account surface and confirmation dialog.

The creator `/app` topbar must not render a red `ADMIN Reset Pipeline` button, even when the signed-in account has the admin role. The account menu may contain a quiet `Administration` link and, if the existing reset command remains available there, it must stay inside the admin-only account surface with its existing server-authorized confirmation flow. Do not invent a new backend mutation endpoint as part of this frontend remediation. See [10-admin-console-specification.md](10-admin-console-specification.md).

## Stage navigator

Use five stages in the current production order:

1. Discover — understand the story;
2. Content — shape the narrative;
3. Design — craft the presentation;
4. Prepare — finalize the handoff;
5. Generate & Preview — build and inspect.

Each item displays one semantic state: locked, available, working, review, attention, or complete. The selected stage is visually dominant. Locked items remain discoverable but are not clickable. Working and attention states must be visible without relying on color alone.

At tablet/mobile widths, replace the full rail with a compact stage selector and current-step summary. Do not move a large rail below the artifact.

## Stage context strip

This is the only persistent stage-local context. It contains:

- current stage name and purpose;
- current server-confirmed status;
- no more than four decision-relevant facts;
- an optional “View output” developer affordance when enabled.

Do not repeat the same facts in a left rail, title badge, banner, and action area.

## Primary canvas

Desktop canvas rules:

- max width approximately 72–80rem;
- one main reading column with a 36–56rem text measure;
- stage-specific grids only for routes, scenes, facts, or evidence that genuinely benefit from spatial comparison;
- no nested fixed sidebars;
- no title column narrower than the status/metadata column;
- no absolute-positioned status badge over a heading.

The stage title follows a single vertical flow: eyebrow, status, title, one-sentence purpose, then the artifact. The title may balance across lines but must not become a poster-sized obstacle.

## ActionDock

The dock is visible for every actionable review state. It uses a reserved sticky region rather than overlaying content.

| State | Primary action | Secondary action |
|---|---|---|
| Review with next stage | Approve & continue to {next agent} | Revise |
| Review without next stage | Approve | Revise |
| Working | none | Stop, when supported |
| Attention with retry | Retry | View details / refresh |
| Attention without retry | Refresh or supported recovery | View details |
| Generation available | Generate portfolio | View handoff |
| Generation ready | Open preview | Regenerate, when allowed |

Button labels must remain readable on one line at desktop widths and become full-width stacked actions on mobile.

## Output Inspector

The inspector is visible only in developer mode and opens on explicit request. It includes:

- active stage output;
- stage label, state, and freshness;
- read-only formatted JSON;
- copy action and copy feedback;
- optional safe trace/reference ID.

It must not show raw worker payloads, prompts, credentials, response bodies, or hidden reasoning. Selection follows the active stage and never falls back to Discovery merely because another output exists.

## Creator input and next-agent controls

Discovery is the one stage with a conversational input surface. Its composer is part of the centered artifact canvas, not a rail or a separate developer panel:

- use a labeled multiline input for the intake or current answer;
- keep the label and purpose sentence visible when the field has focus;
- show bounded word/character feedback beneath the field;
- keep the submit action adjacent to the field on desktop and full width on mobile;
- after a submitted answer, label the next action `Next question`, not a generic `Next`.

Review stages use a destination-specific approval action so the user knows which agent will receive the approved snapshot:

| Current stage | Primary label | Operation |
|---|---|---|
| Discovery | `Approve & continue to Content Architect` | approve the brief; leave the stage ready for explicit Content Architect start |
| Content | `Approve & continue to Visual Design Director` | approve the content scope; leave the stage ready for explicit Visual Design Director start |
| Visual Design | `Approve & continue to Build Preparation` | approve the visual direction; leave the stage ready for explicit preparation start |
| Build Preparation | `Continue to Generate` | approve/use the immutable brief pair, then expose the explicit Code Generator start action |
| Generation | `Generate Portfolio` / `Retry generation` | start or retry only when the server projection permits it |

The UI may combine the approval and navigation request into one explicit click, but it must never make the next agent appear started until the corresponding server response confirms it. A failed start after successful approval is represented as `Approved` plus a separate `Start next stage` action.

## Visual system rules

- Preserve cream/paper, ink, and cobalt tokens.
- Keep one accent for primary actions and confirmed transitions.
- Use hairlines and small labels to clarify structure, not to decorate every edge.
- Use sentence case for most user-facing headings.
- Keep display serif for editorial statements; use sans-serif for labels, controls, and structured facts.
- Keep existing reduced-motion behavior and avoid motion as a prerequisite for understanding.
