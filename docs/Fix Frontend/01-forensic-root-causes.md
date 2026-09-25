# Active workflow interface root causes

The frontend audit findings cluster into systemic causes that affect the active Discovery and Content Architect experience. Correcting these shared causes prevents the same layout and state problems from returning in longer briefs and route plans.

## 1. Overloaded information architecture

The creator shell can present a topbar, stage-local activity, a primary artifact, and an always-open handoff utility at once. Users have too many competing answers to “where am I?” and “what should I inspect next?”. Persistent side rails consume width the artifact needs.

Remediation: one compact navigator for Discovery and Content Architect, one main canvas, one small in-flow context strip, and one optional developer inspector.

## 2. Prose-first result representation

Discovery briefs and Content Architect plans can appear as long text blocks even when their useful structure is a set of profile facts, a site map, a route plan, or section inventory. This is a representation mismatch, not simply a typography problem.

Remediation: make the brief summary, route map, route tabs, section cards, and evidence tiles the primary surfaces. Keep the complete Markdown output available as a secondary reader.

## 3. Nested width-consuming grids

The output rail, workspace rail, artifact table of contents, metadata column, and main content column can all compete for horizontal space. This leaves a narrow reading column beside unused canvas.

Remediation: use one desktop content grid, avoid nested fixed-width columns, provide a generous readable measure, and use grids only where facts or routes benefit from spatial comparison.

## 4. Excessive vertical expansion

Long Markdown can mount in full, every route or section can appear at once, and action controls can sit after the entire output.

Remediation: summarize first, show one route or decision surface at a time, use deliberate progressive disclosure, and reserve space for a sticky action dock.

## 5. Buried decision actions

Approval, revision, retry, and recovery actions can sit after long content. Narrow grid cells make action text wrap and can clip icons.

Remediation: use a persistent, responsive ActionDock with one primary action, one secondary revision or recovery action, and explicit disabled and loading states.

## 6. Duplicated or incorrect field mapping

Identical title and body content can render twice, while stale output can be selected when the user changes stages.

Remediation: normalize once in adapters, render each fact once, deduplicate identical title/body content, and select jobs using the server-provided active job identity.

## 7. Developer tooling rendered as product UI

An open handoff utility can occupy a primary column and display raw JSON during normal work. It creates visual noise, leaks implementation details into the creator workflow, and can retain stale output.

Remediation: keep complete output and copy capability behind a closed-by-default developer-only Output Inspector. Its entry follows the selected active stage and its content is read-only.

## 8. Incomplete asynchronous failure projection

A failed durable job can coexist with a session projection that still says work is active. The frontend then keeps polling without offering recovery.

Remediation: keep backend job state, session projection, and frontend adapter state aligned. Show safe errors and offer only supported retry or refresh actions.

## 9. Unsafe remote media handling

Untrusted remote media should not be loaded directly into the authenticated product surface or bypass the current content security policy.

Remediation: show safe metadata and a source link where external media is relevant. Keep the current self-only image and font policy intact.

## 10. Weak responsive condensation and accessibility feedback

Tablet layouts can move utility content below the main area and add empty space. Mobile can stack every section without changing information density. Broad live announcements can make status changes noisy.

Remediation: collapse navigation to a compact selector and progress strip, keep route tabs horizontally scrollable, make actions full-width and reserved, close secondary readers by default, avoid horizontal overflow, and announce only meaningful status transitions.

## Root-cause-to-fix priority

1. Correct durable state and failure projection.
2. Remove competing rails and establish the single-canvas shell.
3. Put decisions in the ActionDock.
4. Replace long text dumps with representations suited to briefs and route plans.
5. Keep media handling within the existing content security policy.
6. Add browser geometry and state acceptance coverage.
