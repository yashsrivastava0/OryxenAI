import { useEffect, useMemo, useState } from "preact/hooks";
import type { PageContentVM } from "../data/adapters/content";
import { buildPreviewHtml, THEME_BASE_PATH } from "../data/preview-template";

// A lightweight, UNVERIFIED client-side review convenience: the real pinned
// template is fetched once and filled with the Content Architect's copy by
// deterministic DOM substitution (no model call). It is not the future
// browser-verified, signed preview pipeline owned by the Code Generator.

const TEMPLATE_URL = `${THEME_BASE_PATH}index.html`;
let templatePromise: Promise<string> | null = null;

function loadTemplate(): Promise<string> {
  if (!templatePromise) {
    templatePromise = fetch(TEMPLATE_URL, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw new Error(`Template request failed (${response.status})`);
        return response.text();
      })
      .catch((error: unknown) => {
        templatePromise = null; // allow a retry after a transient failure
        throw error;
      });
  }
  return templatePromise;
}

export interface PortfolioPreviewProps {
  page: PageContentVM;
}

export function PortfolioPreview({ page }: PortfolioPreviewProps) {
  const [template, setTemplate] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    loadTemplate().then(
      (text) => {
        if (!cancelled) setTemplate(text);
      },
      () => {
        if (!cancelled) setFailed(true);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const srcDoc = useMemo(() => {
    if (template === null) return null;
    try {
      return buildPreviewHtml(template, page);
    } catch {
      return null;
    }
  }, [template, page]);

  return (
    <section className="portfolio-preview" aria-label="Live page preview">
      <div className="portfolio-preview-toolbar">
        <span className="portfolio-preview-note">
          Draft preview: your approved copy placed into the pinned page design. The final page is
          generated and checked in a later step.
        </span>
      </div>
      {failed || (template !== null && srcDoc === null) ? (
        <div className="portfolio-preview-status" role="alert">
          <p>The page preview could not be loaded.</p>
          <button type="button" className="btn-secondary" onClick={() => setAttempt((n) => n + 1)}>
            Try again
          </button>
        </div>
      ) : srcDoc === null ? (
        <div className="portfolio-preview-status" role="status">
          <p>Preparing preview…</p>
        </div>
      ) : (
        <iframe
          className="portfolio-preview-frame"
          title="Portfolio page preview"
          sandbox="allow-same-origin"
          srcDoc={srcDoc}
        />
      )}
    </section>
  );
}
