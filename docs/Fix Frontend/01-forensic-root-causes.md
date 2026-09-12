# Forensic root-cause analysis

The audit registered twenty findings, but the failures cluster into ten systemic causes. Fixing individual screenshots without correcting these causes would leave the next long profile or multi-route output broken again.

## 1. Overloaded information architecture

The product shell simultaneously presents a topbar, a five-step rail, a stage-local activity rail, a primary artifact, and an always-open handoff utility. The user has too many competing answers to “where am I?” and “what should I inspect next?”. The persistent left and right rails consume width that the artifact needs.

Remediation: one compact stage navigator, one main stage canvas, one small in-flow context strip, and one optional developer inspector.

## 2. Prose-first result representation

Content Architecture is rendered as a sequence of text blocks even though its useful output is a site map, route plan, and section inventory. Visual Design is rendered as prose and collapsed details even though its useful output is a visual language, route storyboard, scene sequence, and asset treatment. This is a representation mismatch, not simply a typography problem.

Remediation: route maps, route tabs, section cards, scene storyboards, intent cards, and evidence tiles become the primary surfaces. Long Markdown remains available as a secondary reader.

## 3. Nested width-consuming grids

The global output rail, the WorkspaceCanvas rail, the ArtifactSurface table of contents, the artifact header metadata column, and the main content column all compete for horizontal space. The result is the audited 160px content column and one-word line wrapping while adjacent canvas remains empty.

Remediation: one desktop content grid, no nested fixed-width columns, a generous readable measure, and stage-specific grids only where the data has a true spatial relationship.

## 4. Excessive vertical expansion

Long Markdown is mounted in full, all routes/sections are shown at once, and action controls are appended after the full output. The measured review heights were approximately 4.36 viewport heights for Discovery, 11.55 for Content, 5.09 for Design, and 3.14 for Preparation.

Remediation: summarize first, show one route or one decision surface at a time, use deliberate progressive disclosure, and reserve space for a sticky action dock.

## 5. Buried decision actions

Approval, revision, retry, and generation actions are located after the longest content. Narrow grid cells force action text to wrap across several lines and clip the arrow icon.

Remediation: use a persistent, responsive ActionDock with one primary action, one secondary revision/recovery action, and explicit disabled/loading states.

## 6. Duplicated or incorrect field mapping

The same route/status/count facts appear in both rail and artifact. Content section heading and body can render the same string twice. The Code Generator adapter compares `current_run_id` to job IDs, which are different identities.

Remediation: normalize once in adapters, render each fact once, deduplicate identical title/body content, and select jobs using a server-provided active job identity.

## 7. Developer tooling rendered as product UI

The open `HANDOFF UTILITY` occupies a primary 360px column and displays raw JSON during every stage. It creates visual noise, leaks implementation concepts into the creator workflow, and can retain a stale earlier-stage selection.

Remediation: keep complete output and copy capability behind a closed-by-default developer-only Output Inspector. Its active entry must follow the selected stage and its content must be read-only.

## 8. Incomplete async failure projection

The worker can persist a failed durable job while the session projection still says the stage is active. The frontend sees a working stage, keeps polling, and offers no recovery. The problem is the combined backend projection and frontend adapter contract, not just a missing error banner.

Remediation: project the active job, reconcile terminal Code Generator failures into a safe run attention state, map failed/cancelled jobs to attention, stop polling, and show a valid server-supported recovery action.

## 9. CSP-incompatible external media

Build Preparation emits discovery metadata and external preview URLs, while the product CSP allows only same-origin images. Rendering those URLs creates blocked requests, broken-image boxes, and raw keyword alt text.

Remediation: do not render external preview URLs directly. Render evidence tiles with metadata and a source link. A future same-origin proxy would require a separate security/performance decision.

## 10. Weak responsive condensation and accessibility feedback

The tablet layout moves utility content below the main area, adding large empty regions. Mobile stacks every section without changing information density. Several changing regions use live announcements too broadly.

Remediation: collapse navigation to a stage selector/progress strip, keep route tabs horizontally scrollable, make actions full-width and reserved, close secondary readers by default, avoid horizontal overflow, and announce only meaningful status transitions.

## Root-cause-to-fix priority

1. Correct durable state and failure projection.
2. Remove competing rails and establish the single-canvas shell.
3. Put decisions in the ActionDock.
4. Replace prose dumps with stage-native representations.
5. Fix CSP-safe resource evidence.
6. Add browser geometry and state acceptance coverage.
