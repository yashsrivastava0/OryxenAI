import { useState, useMemo } from "preact/hooks";
import type { ComponentChildren } from "preact";
import { SafeMarkdown, extractHeadings } from "./SafeMarkdown";
import { RevisionComposer } from "./RevisionComposer";
import { ActionDock } from "./ActionDock";
import { copyJson, formatJson, type CopyJsonResult } from "../data/clipboard";

export interface ArtifactSectionItem {
  id: string;
  title: string;
  subtitle?: string;
  badge?: string;
  contentMarkdown?: string;
  details?: Record<string, unknown>;
}

export interface ArtifactSurfaceProps {
  title: string;
  statusBadge?: string;
  isApproved: boolean;
  canMutate: boolean;
  markdownContent?: string;
  structuredSections?: ArtifactSectionItem[];
  metadata?: Array<{ label: string; value: string }>;
  warnings?: string[];
  artifactTypeName: string; // e.g. "portfolio brief" or "content plan"
  finalJsonOutput?: unknown;
  /** The next agent this artifact hands off to. The approved state exposes a
   * separate destination-specific start action for this stage. */
  nextStageName?: string;
  onApproveAndContinue?: () => Promise<void>;
  onStartNextStage?: () => Promise<void>;
  startNextStageLabel?: string;
  nextStageInFlight?: boolean;
  onRevise?: (revisionRequest: string) => Promise<void>;
  /** Rich custom content rendered above the markdown/structured sections —
   * a sitemap, palette swatches, a peek-card deck. Lets a stage replace
   * flattened markdown with real components while keeping the shared
   * header/warnings/approval chrome. */
  children?: ComponentChildren;
}

export function ArtifactSurface({
  title,
  statusBadge,
  isApproved,
  canMutate,
  markdownContent = "",
  structuredSections = [],
  metadata = [],
  warnings = [],
  artifactTypeName,
  finalJsonOutput,
  nextStageName,
  onApproveAndContinue,
  onStartNextStage,
  startNextStageLabel,
  nextStageInFlight = false,
  onRevise,
  children,
}: ArtifactSurfaceProps) {
  const [showRevisionComposer, setShowRevisionComposer] = useState(false);
  const [approving, setApproving] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | CopyJsonResult>("idle");
  const [error, setError] = useState<string | null>(null);

  // Extract headings from markdown if present
  const markdownHeadings = useMemo(() => extractHeadings(markdownContent), [markdownContent]);
  const finalJson = useMemo(() => {
    if (finalJsonOutput === undefined || finalJsonOutput === null) return "";
    return formatJson(finalJsonOutput);
  }, [finalJsonOutput]);

  const handleApproveAndContinue = async () => {
    if (!onApproveAndContinue || approving) return;
    setApproving(true);
    setError(null);
    try {
      await onApproveAndContinue();
      // On success this component usually unmounts anyway (the shell
      // navigates to the next stage, or the parent flips `isApproved` and
      // stops rendering this action). Reset `approving` regardless: relying
      // on every future caller to unmount rather than resolve is exactly
      // the kind of coupling that produces a permanently stuck button the
      // one time a caller doesn't.
      setApproving(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval could not be saved. Please try again.");
      setApproving(false);
    }
  };

  const handleScrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const handleCopyJson = async () => {
    if (!finalJson) return;
    const result = await copyJson(finalJson);
    setCopyStatus(result);
    window.setTimeout(() => setCopyStatus("idle"), 1800);
  };

  return (
    <article className="artifact-surface" aria-labelledby="artifact-main-title">
      {/* Header bar */}
      <header className="artifact-header">
        <div className="artifact-title-group">
          <div className="artifact-eyebrow-row">
            <span className="eyebrow">{artifactTypeName.toUpperCase()}</span>
            {statusBadge && <span className={`artifact-badge ${isApproved ? "approved" : "draft"}`}>{statusBadge}</span>}
          </div>
          <h1 id="artifact-main-title">{title}</h1>
        </div>

        {/* Metadata items if any */}
        {metadata.length > 0 && (
          <div className="artifact-metadata-row">
            {metadata.map((item, idx) => (
              <span key={idx} className="metadata-item">
                <span className="metadata-label">{item.label}:</span>{" "}
                <span className="metadata-value">{item.value}</span>
              </span>
            ))}
          </div>
        )}
      </header>

      {/* Warnings banner if present */}
      {warnings.length > 0 && (
        <div className="artifact-warnings-banner" role="note">
          <p className="warnings-title">Notes & Exclusions:</p>
          <ul>
            {warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Layout: Sidebar Table of Contents + Reading Body */}
      <div className="artifact-layout">
        {/* Table of contents (if headings or sections exist) */}
        {(markdownHeadings.length > 1 || structuredSections.length > 1) && (
          <nav className="artifact-toc" aria-label="Sections index">
            <p className="toc-heading">Index</p>
            <ul>
              {markdownHeadings.map((h) => (
                <li key={h.id} className={`toc-item level-${h.level}`}>
                  <button type="button" onClick={() => handleScrollTo(h.id)}>
                    {h.text}
                  </button>
                </li>
              ))}
              {structuredSections.map((sec) => (
                <li key={sec.id} className="toc-item level-2">
                  <button type="button" onClick={() => handleScrollTo(`sec-${sec.id}`)}>
                    {sec.title}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        )}

        {/* Reading column */}
        <div className="artifact-body">
          {/* Rich custom content (sitemap, palette, peek-card decks, ...) */}
          {children}

          {/* Main prose */}
          {markdownContent && <SafeMarkdown content={markdownContent} />}

          {/* Structured section cards if any */}
          {structuredSections.length > 0 && (
            <div className="structured-sections">
              {structuredSections.map((sec) => (
                <section key={sec.id} id={`sec-${sec.id}`} className="structured-section-card">
                  <div className="sec-header">
                    <h3>{sec.title}</h3>
                    {sec.badge && <span className="sec-badge">{sec.badge}</span>}
                  </div>
                  {sec.subtitle && <p className="sec-subtitle">{sec.subtitle}</p>}
                  {sec.contentMarkdown && <SafeMarkdown content={sec.contentMarkdown} />}
                </section>
              ))}
            </div>
          )}

          {finalJson && (
            <details className="artifact-json-output">
              <summary>Final JSON output</summary>
              <p>
                This persisted agent artifact excludes intake, authentication, and job metadata.
                Copy it for a temporary handoff or open the field below for manual copy.
              </p>
              <div className="artifact-json-actions">
                <button type="button" className="btn-secondary" onClick={() => void handleCopyJson()}>
                  {copyStatus === "copied" || copyStatus === "fallback" ? "JSON copied" : "Copy final JSON"}
                </button>
                {copyStatus === "unavailable" && (
                  <span role="status">Clipboard unavailable — select and copy from the field.</span>
                )}
              </div>
              <textarea
                className="artifact-json-field"
                readOnly
                rows={14}
                value={finalJson}
                aria-label={`${artifactTypeName} final JSON output`}
                onFocus={(event) => event.currentTarget.select()}
              />
            </details>
          )}

          {error && <p className="artifact-error" role="alert">{error}</p>}

          {/* Review actions commit only this artifact. Starting the next stage
              is exposed after the approved state is rendered below. */}
          {!isApproved && canMutate && onApproveAndContinue && (
            <div className="artifact-review-actions">
              <div className="action-buttons-row">
                <button
                  type="button"
                  className={`btn-primary handoff-cta ${approving ? "is-approving" : ""}`}
                  disabled={approving}
                  onClick={() => void handleApproveAndContinue()}
                >
                  <span className="handoff-cta-label">
                    {approving ? "Saving approval..." : `Approve ${artifactTypeName}`}
                  </span>
                </button>
                {onRevise && (
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={approving}
                    onClick={() => setShowRevisionComposer(true)}
                  >
                    Revise
                  </button>
                )}
              </div>

              {/* Revision Composer, the one alternative to approving as-is */}
              {showRevisionComposer && onRevise && (
                <RevisionComposer
                  artifactName={artifactTypeName}
                  onSubmit={async (req) => {
                    await onRevise(req);
                    setShowRevisionComposer(false);
                  }}
                  onCancel={() => setShowRevisionComposer(false)}
                />
              )}
            </div>
          )}

          {isApproved && canMutate && onStartNextStage && nextStageName ? (
            <ActionDock
              primaryLabel={startNextStageLabel ?? `Start ${nextStageName}`}
              onPrimary={onStartNextStage}
              busy={nextStageInFlight}
              busyLabel={`Starting ${nextStageName}...`}
              note="Approval is saved. Start the next stage when you are ready."
            />
          ) : null}
        </div>
      </div>
    </article>
  );
}
