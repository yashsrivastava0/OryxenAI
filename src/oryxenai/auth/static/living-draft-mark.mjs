/**
 * The Living Draft mark — OryxenAI's one decorative signature element, used
 * during auth resolution and stage transitions. Plain ESM so the auth pages
 * (no build step) and the Preact product bundle can both render the exact
 * same markup from one source (frontend/src/components/LivingDraftMark.tsx
 * imports this file directly).
 *
 * Spec: docs/Frontend/03-visual-system-architecture-and-evidence.md §3
 * "Illustration and loading mark" — a horizontal rule enters as an unformed
 * line, passes through five construction points, and resolves into a simple
 * browser-frame rectangle; one short segment animates with
 * stroke-dashoffset while a wait is active; aria-hidden; reduced motion
 * shows the completed static geometry. Styling/animation lives in the
 * sibling living-draft-mark.css, not inline, so it stays subject to the
 * page's normal CSP (no inline <style>/nonce needed).
 */

export const LIVING_DRAFT_MARK_ACTIVE_CLASS = "dlm-active";

export function livingDraftMarkMarkup({ active = false } = {}) {
  const cls = active ? ` ${LIVING_DRAFT_MARK_ACTIVE_CLASS}` : "";
  return `<svg class="dlm${cls}" viewBox="0 0 128 40" width="64" height="20" fill="none" aria-hidden="true" focusable="false">
  <line class="dlm-rule" x1="6" y1="20" x2="122" y2="20" stroke-width="1.5" stroke-linecap="round" />
  <circle class="dlm-point" cx="6" cy="20" r="2.25" />
  <circle class="dlm-point" cx="35" cy="20" r="2.25" />
  <circle class="dlm-point" cx="64" cy="20" r="2.25" />
  <circle class="dlm-point" cx="93" cy="20" r="2.25" />
  <circle class="dlm-point" cx="122" cy="20" r="2.25" />
  <rect class="dlm-frame" x="40" y="8" width="48" height="24" rx="3" stroke-width="1.5" />
  <line class="dlm-frame" x1="40" y1="14.5" x2="88" y2="14.5" stroke-width="1.25" />
  <circle class="dlm-frame-dot" cx="44.5" cy="11.25" r="0.9" />
  <circle class="dlm-frame-dot" cx="48" cy="11.25" r="0.9" />
  <path class="dlm-sweep" d="M6,20 L122,20" stroke-width="2" stroke-linecap="round" pathLength="100" />
</svg>`;
}
