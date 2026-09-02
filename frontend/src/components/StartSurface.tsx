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

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning, architect.";
    if (hour < 18) return "Good afternoon, architect.";
    return "Good evening, architect.";
  }, []);

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
      label = "Preliminary notes · Add milestones for richer discovery";
      pct = Math.min(100, Math.round((words / 80) * 100));
    } else if (words < 70) {
      label = "Solid narrative foundation · Ready for Discovery";
      pct = Math.min(100, Math.round((words / 80) * 100));
    } else {
      label = "High narrative density · Full atelier depth";
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
      setError("Please provide a short summary, background, or select an archetype to begin.");
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
      <section className="start-surface" aria-labelledby="start-heading">
        <header className="start-hero-header">
          <div className="hero-status-beacon">
            <span className="beacon-dot" aria-hidden="true" />
            <span className="beacon-text">ATELIER ACTIVE · SYSTEM READY</span>
          </div>

          <p className="start-greeting">{greeting}</p>
          <h1 id="start-heading" className="start-hero-title">
            Let's find the story your portfolio should tell.
          </h1>
          <p className="start-hero-thesis">
            Transform raw experience into a deliberate, verified portfolio. Our specialized pipeline guides you
            through <strong>Discovery</strong>, <strong>Content Architecture</strong>, <strong>Visual Direction</strong>, <strong>Build Packaging</strong>, and <strong>Code Generation</strong> with zero automated slop.
          </p>
        </header>

        <ArchetypeSelector
          selectedId={selectedArchetypeId}
          onSelectArchetype={handleSelectArchetype}
          onSelectQuickStarter={handleSelectQuickStarter}
          disabled={inFlight || disabled}
        />

        <form onSubmit={handleSubmit} className="start-form">
          <div className="start-form-header">
            <label htmlFor="intake-notes" className="start-label">
              Narrative Intake & Background Notes
            </label>
            <span className="start-label-hint">Paste rough notes, project briefs, or select an archetype above</span>
          </div>

          <div className="textarea-tactile-container">
            <textarea
              id="intake-notes"
              className="start-textarea"
              rows={8}
              placeholder="Paste anything you have: a bio, rough resume bullets, recent projects, or what you want people to know about your work..."
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
              <p className="start-trust-note">
                <span className="trust-lock-icon" aria-hidden="true">🔒</span>
                Private & verified. Nothing is published without your explicit review and stage approval.
              </p>
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
                  Clear notes
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
                    <span>Initializing Atelier...</span>
                  </>
                ) : (
                  <>
                    <span>Start my portfolio</span>
                    <span className="btn-arrow" aria-hidden="true">→</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </section>

      <PipelineStagePreview />
    </div>
  );
}
