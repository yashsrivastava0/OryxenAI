import { useId, useState } from "preact/hooks";
import type { ComponentChildren } from "preact";

export interface PeekCardProps {
  /** Small kicker above the title, e.g. a section id or route path. */
  eyebrow?: string;
  title: string;
  /** Optional short badge, e.g. priority or status. */
  badge?: string;
  /** The compact summary always visible — keep this to roughly one line so
   * a deck of these cards reads as a scannable list, not a second wall of
   * text (this is the direct fix for "some part, not the full response"). */
  summary: ComponentChildren;
  /** The full detail, only mounted/visible once expanded. */
  children: ComponentChildren;
  /** Rendered instead of children's disclosure control when this card
   * should start open (e.g. the single result in a list of one). */
  defaultOpen?: boolean;
}

/**
 * Shared progressive-disclosure card: a compact peek (eyebrow + title +
 * one-line summary) that expands in place to the full detail without a
 * route change or page-length jump. Used by Content Architect's section
 * deck, Visual Design Director's scene cards, and Build Preparation's
 * asset/component decks — anywhere a stage previously flattened a rich
 * structured object into a long wall of markdown.
 */
export function PeekCard({ eyebrow, title, badge, summary, children, defaultOpen = false }: PeekCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  const detailId = useId();

  return (
    <article className={`peek-card ${open ? "is-open" : ""}`} data-open={open}>
      <button
        type="button"
        className="peek-card-toggle"
        aria-expanded={open}
        aria-controls={detailId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="peek-card-heading">
          {eyebrow && <span className="peek-card-eyebrow">{eyebrow}</span>}
          <span className="peek-card-title">{title}</span>
        </span>
        <span className="peek-card-meta">
          {badge && <span className="peek-card-badge">{badge}</span>}
          <svg
            className="peek-card-chevron"
            width="14"
            height="14"
            viewBox="0 0 14 14"
            fill="none"
            aria-hidden="true"
          >
            <path d="M3.5 5.25 7 8.75l3.5-3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>
      <p className="peek-card-summary">{summary}</p>
      <div id={detailId} className="peek-card-detail" hidden={!open}>
        {open && children}
      </div>
    </article>
  );
}
