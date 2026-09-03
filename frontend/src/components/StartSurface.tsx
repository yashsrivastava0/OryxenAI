import { useState, useMemo } from "preact/hooks";
import { ArchetypeSelector, type Archetype } from "./ArchetypeSelector";
import { PipelineStagePreview } from "./PipelineStagePreview";

export interface StartSurfaceProps {
  onStart: (intakeText: string) => Promise<void>;
  disabled?: boolean;
}

export function StartSurface({ onStart, disabled = false }: StartSurfaceProps) {
  const [intakeText, setIntakeText] = useState("");
  const [selectedArchetypeId, setSelectedArchetypeId] = useState<string | null>(null);
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { wordCount, charCount, densityLabel, densityPercent } = useMemo(() => {
    const trimmed = intakeText.trim();
    const chars = trimmed.length;
    const words = trimmed ? trimmed.split(/\s+/).length : 0;

    let label = "Awaiting notes";
    let pct = 0;

    if (words === 0) {
      label = "Awaiting intake notes";
      pct = 0;
    } else if (words < 25) {
      label = "Preliminary notes · Add key projects for richer discovery";
      pct = Math.min(100, Math.round((words / 70) * 100));
    } else if (words < 70) {
      label = "Solid foundation · Ready for Discovery";
      pct = Math.min(100, Math.round((words / 70) * 100));
    } else {
      label = "Detailed notes · Ready for full-fidelity Discovery";
      pct = 100;
    }

    return { wordCount: words, charCount: chars, densityLabel: label, densityPercent: pct };
  }, [intakeText]);

  const handleSelectArchetype = (arch: Archetype) => {
    setSelectedArchetypeId(arch.id);
    setIntakeText(arch.draftText);
    setError(null);
  };

  const handleSelectQuickStarter = (starterText: string) => {
    setIntakeText((prev) => {
      const trimmed = prev.trim();
      if (!trimmed) return `Role focus: ${starterText}\n\nKey experience and projects:\n- `;
      return `${trimmed}\n- Role focus: ${starterText}`;
    });
    setError(null);
  };

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (inFlight || disabled) return;
    const text = intakeText.trim();
    if (!text) {
      setError("Please paste notes, project bullets, or select a role template to begin.");
      return;
    }
    setError(null);
    setInFlight(true);
    try {
      await onStart(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start your portfolio. Please try again.");
    } finally {
      setInFlight(false);
    }
  };

  return (
    <div className="atelier-start-wrapper">
      {/* ── Above-the-Fold Hero Section with Integrated Command Center ───────── */}
      <section className="start-hero-section" aria-labelledby="start-heading">
        <header className="start-hero-header">
          <div className="hero-status-beacon" aria-label="System status">
            <span className="beacon-dot" aria-hidden="true" />
            <span className="beacon-text">STUDIO ATELIER · READY</span>
          </div>

          <h1 id="start-heading" className="start-hero-title">
            Direct your experience into a verified portfolio.
          </h1>
          <p className="start-hero-thesis">
            Autonomous 5-stage pipeline from career notes to verified, responsive production code.
          </p>
        </header>

        {/* ── Primary Command Center Input (Double-Bezel Architecture) ──────── */}
        <div className="command-center-outer">
          <div className="command-center-core">
            <ArchetypeSelector
              selectedId={selectedArchetypeId}
              onSelectArchetype={handleSelectArchetype}
              onSelectQuickStarter={handleSelectQuickStarter}
              disabled={inFlight || disabled}
            />

            <form onSubmit={handleSubmit} className="start-form" novalidate>
              <div className="textarea-tactile-container">
                <label htmlFor="intake-notes" className="visually-hidden">
                  Portfolio intake notes
                </label>
                <textarea
                  id="intake-notes"
                  className="start-textarea"
                  rows={4}
                  placeholder="Paste your bio, resume bullets, GitHub links, recent projects, or what you want people to know about your work..."
                  value={intakeText}
                  onInput={(e) => {
                    setIntakeText((e.target as HTMLTextAreaElement).value);
                    if (error) setError(null);
                  }}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                      e.preventDefault();
                      if (!inFlight && !disabled && intakeText.trim()) {
                        handleSubmit(e as unknown as Event);
                      }
                    }
                  }}
                  disabled={inFlight || disabled}
                />

                <div className="narrative-telemetry-bar">
                  <div className="telemetry-metrics">
                    <span className="telemetry-counter">
                      <strong>{wordCount}</strong> words · <strong>{charCount}</strong> chars
                    </span>
                    <span className="telemetry-status">{densityLabel}</span>
                  </div>
                  <div className="telemetry-progress-track" aria-hidden="true">
                    <div
                      className="telemetry-progress-fill"
                      style={{ width: `${densityPercent}%` }}
                    />
                  </div>
                </div>
              </div>

              {error && <p className="start-error" role="alert">{error}</p>}

              <div className="start-actions-row">
                <div className="start-actions-left">
                  <span className="start-trust-badge">
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" className="trust-lock-svg">
                      <path fillRule="evenodd" d="M4 4a4 4 0 0 1 8 0v2h.25c.966 0 1.75.784 1.75 1.75v5.5A1.75 1.75 0 0 1 12.25 15h-8.5A1.75 1.75 0 0 1 2 13.25v-5.5C2 6.784 2.784 6 3.75 6H4V4Zm1.5 2h5V4a2.5 2.5 0 0 0-5 0v2Z" clipRule="evenodd" />
                    </svg>
                    Private workspace. Nothing is built or published without your approval.
                  </span>
                </div>
                <div className="start-actions-right">
                  <span className="keyboard-hint" aria-hidden="true">
                    <kbd>Ctrl</kbd> + <kbd>↵</kbd>
                  </span>
                  {intakeText.trim().length > 0 && (
                    <button
                      type="button"
                      className="btn-text-secondary"
                      onClick={() => {
                        setIntakeText("");
                        setSelectedArchetypeId(null);
                      }}
                      disabled={inFlight || disabled}
                    >
                      Clear
                    </button>
                  )}
                  <button
                    type="submit"
                    className="btn-primary start-submit-btn"
                    disabled={inFlight || disabled || !intakeText.trim()}
                  >
                    {inFlight ? (
                      <>
                        <span className="btn-spinner" aria-hidden="true" />
                        <span>Starting Discovery...</span>
                      </>
                    ) : (
                      <>
                        <span>Start Discovery</span>
                        <span className="btn-icon-wrapper" aria-hidden="true">
                          <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                            <path fillRule="evenodd" d="M1 8a.75.75 0 0 1 .75-.75h11.19L9.47 3.78a.75.75 0 0 1 1.06-1.06l4.5 4.5a.75.75 0 0 1 0 1.06l-4.5 4.5a.75.75 0 0 1-1.06-1.06L12.94 8.75H1.75A.75.75 0 0 1 1 8Z" clipRule="evenodd" />
                          </svg>
                        </span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </section>

      {/* ── Below the Fold: Progressive Pipeline Showcase ───────────────────── */}
      <PipelineStagePreview />
    </div>
  );
}
