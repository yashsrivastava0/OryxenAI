# Code Generator preview research and implementation brief

## Purpose

This document accompanies the three Code Generator reference images. The images are implementation references only; they are not production assets and do not define runtime data. The existing stage/API contracts remain authoritative.

References:

- [13-code-generator-preview-workspace.png](visuals/13-code-generator-preview-workspace.png) — default split workspace with activity, input, and live preview.
- [14-code-generator-preview-working.png](visuals/14-code-generator-preview-working.png) — generation in progress with a stable preview frame.
- [15-code-generator-preview-attention.png](visuals/15-code-generator-preview-attention.png) — terminal failure with preserved preview and recovery.

## External patterns reviewed

### Emergent

[Emergent's deployment guidance](https://help.emergent.sh/deployment-on-emergent) treats Preview as a temporary private testing environment and Deployment as the durable public release. The preview opens from the builder, shows the current app, and is intended for interaction and troubleshooting before launch. The implementation implication is that OryxenAI must label preview and publish as different states and must never make a temporary preview look like a published portfolio.

[Emergent's first-app flow](https://help.emergent.sh/first-app) also exposes a human-readable stream of work such as project setup, frontend work, styling, and tests before presenting a preview link. OryxenAI should keep this transparency, but use the existing semantic milestones rather than raw worker logs.

### Replit

[Replit's Project Editor](https://docs.replit.com/learn/projects-and-artifacts/project-editor) uses a conversation/tool area beside a live app preview. The preview is treated as a real app: the user can interact with it while the agent works. [Replit's landing-page guide](https://docs.replit.com/build/landing-page) further separates Preview from Canvas and gives the user a direct loop of preview, inspect, refine, and publish.

[Replit's development URL guidance](https://docs.replit.com/core-concepts/project-editor/app-setup/development-urls) makes the temporary nature and access boundary explicit. [Its troubleshooting guidance](https://docs.replit.com/build/troubleshooting) starts diagnosis in Preview before publishing. For OryxenAI this means the preview theater needs a visible live/temporary label, an open-in-new-tab affordance, a device-size control, and a publishing action that is disabled or absent until verification succeeds.

### Labell.io

The exact domain supplied for `Labell.io` currently resolves to an unrelated WordPress blog ([labell.io](https://labell.io/)), not a verifiable AI builder product. No interface pattern from that domain was used. If a different product was intended, it can be added later as a separate, identified source; it should not be treated as evidence for the current implementation.

## Converged product pattern

The useful pattern is not “copy a competitor.” It is a stable control room with four clear zones:

1. **Activity and instruction** — a narrow left column shows what the generator has done, what it is doing now, and a multiline input for the next instruction.
2. **Preview theater** — the generated portfolio is the dominant surface and is interactive, scrollable, and visually close to a visitor's experience.
3. **Preview controls** — Desktop, Tablet, Mobile, fit/zoom, refresh/open-preview controls are kept in the theater chrome, not mixed into agent activity.
4. **Release boundary** — Publish is a separate action from preview. It stays unavailable until the server reports a verified preview and ready state.

Do not turn the product into a code editor or log viewer. The activity stream is a concise explanation of work, not a dump of model messages, SQL, JSON, stack traces, or provider details.

## Preview theater contract

The implementing AI should treat the generated portfolio as an untrusted document rendered inside a constrained surface.

```text
PreviewTheater
  toolbar: [Desktop | Tablet | Mobile] [Fit] [Zoom] [Open preview]
  frame: fixed aspect-ratio viewport with overflow: auto
    iframe or isolated preview document
  footer: live/temporary status + last update + publish eligibility
```

Required behavior:

- Keep the outer theater stable with `aspect-ratio`, `min-width: 0`, `max-width: 100%`, and `overflow: hidden` on the frame wrapper.
- Let only the inner preview document scroll. A generated page with an unusually tall hero, a wide table, or an unbounded image must not enlarge the application shell.
- Change the inner viewport width for Desktop, Tablet, and Mobile without changing the outer product layout.
- Use a neutral evidence tile when media is unavailable or blocked by CSP. Do not render broken-image icons, raw keyword strings, or external media directly under the current self-only policy.
- Preserve the last verified preview when a later build fails. The failure state must not replace a useful preview with a blank or locked surface.
- Keep preview URLs, tokens, and runtime details out of normal product copy. “Open preview” may open the server-authorized preview in a new tab.
- Pause polling when the tab is hidden and stop immediately when the active job reaches a terminal failed, cancelled, or successful state.
- Announce meaningful state transitions through the existing status region; do not announce every poll or repaint the full screen.

Suggested safe layout values:

| Surface | Rule |
|---|---|
| Outer workspace | `min-width: 0; width: min(100%, 80rem)` |
| Activity column | `clamp(18rem, 30vw, 24rem)` on desktop; stacked above preview below tablet width |
| Preview column | `minmax(0, 1fr)`; never a fixed pixel width |
| Preview frame | `aspect-ratio: 16 / 10; max-height: calc(100vh - 15rem)` with inner scroll |
| Composer | multiline, full available width, 44px minimum control height for send |
| Mobile preview | inner viewport around 390px wide, horizontally centered, outer page remains one column |

These values are starting constraints, not a license to hardcode a single viewport. Validate at 1536×695, 1366×768, 768×1024, and 390×844.

## State-specific direction

### Available

Show the approved handoff summary and a single, obvious `Generate Portfolio` action. Do not show “Stage locked” after approved preparation. Explain that generation will plan, acquire, build, verify, and promote a preview.

### Working

Show semantic milestones: `Planning`, `Acquiring resources`, `Building pages`, `Testing viewports`, and `Promoting preview`. The current milestone is visually dominant; completed milestones are quiet and pending milestones are neutral. The preview may be a valid partial build or a deliberate neutral loading surface, but the theater must already occupy the expected bounded area. Provide `Stop generation` and keep the follow-up composer available if the product contract permits it.

### Available preview / ready

Make the generated site feel real: preview it inside the theater, allow scrolling and interactions, provide device-size controls, and let the user open the preview in a separate tab. Use a clear `Publish`/`Publish when ready` action only when the backend reports readiness.

### Attention

Say what stopped, confirm what is safe, show that polling stopped, and expose the valid next action. Preserve any prior verified preview. Use `Retry generation` only when the server projection says retry is allowed; otherwise show refresh/support recovery. Keep technical details collapsed behind the existing developer-only inspector.

## Edge cases to test

| Case | Expected result |
|---|---|
| Generated page is very tall | Inner preview scrolls; shell and action area remain fixed and usable |
| Generated page is wider than the device viewport | Inner preview clips or scrolls; no document-level horizontal overflow |
| Image/font is blocked by CSP | Neutral evidence tile with title/source/license/dimensions; no broken media |
| Preview URL expires or returns an authorization error | Preview shows a calm recovery message and refresh/open action; no endless spinner |
| Generation fails after a previous success | Attention state preserves the last verified preview and offers retry if eligible |
| Generation fails before any preview | Attention state shows a bounded empty/placeholder theater and a recovery action |
| User switches tabs while a job runs | Polling pauses while hidden and resumes with one fresh fetch on visibility return |
| User reloads during approval/start | Server state is re-fetched; no duplicate start due to idempotency key |
| Approve succeeds but next-stage start fails | Show approved state plus separate `Start next stage`; never claim both succeeded |
| Mobile keyboard opens over composer | Composer remains reachable; action controls are not hidden behind the keyboard |
| User opens developer inspector | Drawer overlays the product without resizing or corrupting the preview; Escape closes it |

## Implementation checklist

- Keep job selection server-authoritative by `coordinator_stage`; never compare `current_run_id` with a background job ID.
- Project `active_job_id`, `active_job_kind`, and `retry_available` from the API response.
- Normalize terminal failed/cancelled jobs to `attention` and stop polling.
- Keep auth, ownership, entitlement, approval, revision, idempotency, worker fencing, and preview isolation unchanged.
- Build the split shell with CSS grid and `minmax(0, 1fr)`; remove persistent raw output rails from creator mode.
- Implement the preview theater as a bounded component before polishing stage copy.
- Add fixture-backed browser tests for available, working, attention, tall-page, wide-page, blocked-media, and mobile states.
- Compare the implementation to the three images at the same viewport ratios; the images guide hierarchy and proportion, while this document defines behavior.
