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
            Transform notes, code, and project milestones into a production-grade site through an approved 5-stage pipeline.
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
                  rows={7}
                  placeholder="Paste your bio, resume bullets, GitHub links, recent projects, or what you want people to know about your work..."
                  value={intakeText}
                  onInput={(e) => {
                    setIntakeText((e.target as HTMLTextAreaElement).value);
                    if (error) setError(null);
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
                    <span className="trust-lock-icon" aria-hidden="true">🔒</span>
                    Private & verified. Nothing is published without your review.
                  </span>
                </div>
                <div className="start-actions-right">
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
                        <span>Initializing Discovery...</span>
                      </>
                    ) : (
                      <>
                        <span>Start Discovery</span>
                        <span className="btn-icon-wrapper" aria-hidden="true">
                          <span className="btn-arrow">→</span>
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
