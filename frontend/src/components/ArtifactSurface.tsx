import { useState, useMemo } from "preact/hooks";
import { SafeMarkdown, extractHeadings } from "./SafeMarkdown";
import { RevisionComposer } from "./RevisionComposer";

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
  artifactTypeName: string; // e.g. "brief", "content plan", "visual direction"
  finalJsonOutput?: unknown;
  approvalActionLabel?: string;
  requireApprovalConfirmation?: boolean;
  onApprove?: () => Promise<void>;
  onRevise?: (revisionRequest: string) => Promise<void>;
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
  approvalActionLabel,
  requireApprovalConfirmation = true,
  onApprove,
  onRevise,
}: ArtifactSurfaceProps) {
  const [showRevisionComposer, setShowRevisionComposer] = useState(false);
  const [confirmingApproval, setConfirmingApproval] = useState(false);
  const [approving, setApproving] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "unavailable">("idle");
  const [error, setError] = useState<string | null>(null);

  // Extract headings from markdown if present
  const markdownHeadings = useMemo(() => extractHeadings(markdownContent), [markdownContent]);
  const finalJson = useMemo(() => {
    if (finalJsonOutput === undefined || finalJsonOutput === null) return "";
    try {
      return JSON.stringify(finalJsonOutput, null, 2);
    } catch {
      return "";
    }
  }, [finalJsonOutput]);

  const handleApprove = async () => {
    if (!onApprove || approving) return;
    setApproving(true);
    setError(null);
    try {
      await onApprove();
      setConfirmingApproval(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval could not be saved. Please try again.");
    } finally {
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
    if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) {
      setCopyStatus("unavailable");
      return;
    }
    try {
      await navigator.clipboard.writeText(finalJson);
      setCopyStatus("copied");
      window.setTimeout(() => setCopyStatus("idle"), 1800);
    } catch {
      setCopyStatus("unavailable");
    }
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
                  {copyStatus === "copied" ? "JSON copied" : "Copy final JSON"}
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

          {/* Review actions when stage is in review and mutable */}
          {!isApproved && canMutate && onApprove && (
            <div className="artifact-review-actions">
              {!showRevisionComposer && !confirmingApproval && (
                <div className="action-buttons-row">
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={approving}
                    onClick={() => requireApprovalConfirmation
                      ? setConfirmingApproval(true)
                      : void handleApprove()}
                  >
                    {approving ? "Approving..." : approvalActionLabel ?? `Approve ${artifactTypeName}`}
                  </button>
                  {onRevise && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setShowRevisionComposer(true)}
                    >
                      Request a revision
                    </button>
                  )}
                </div>
              )}

              {/* Inline Approval Confirmation */}
              {confirmingApproval && (
                <div className="approval-confirmation-box" role="dialog" aria-labelledby="approval-heading">
                  <h3 id="approval-heading">Approve this {artifactTypeName}?</h3>
                  <p className="confirmation-explanation">
                    Approving locks this draft as the verified foundation for the next stage.
                    The next stage will not start until you explicitly choose to continue.
                  </p>
                  <div className="confirmation-actions">
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={approving}
                      onClick={handleApprove}
                    >
                      {approving ? "Approving..." : `Yes, approve ${artifactTypeName}`}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      disabled={approving}
                      onClick={() => setConfirmingApproval(false)}
                    >
                      Keep reviewing
                    </button>
                  </div>
                </div>
              )}

              {/* Revision Composer Modal/Sheet */}
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
        </div>
      </div>
    </article>
  );
}
