import { useState } from "preact/hooks";

export interface StartSurfaceProps {
  onStart: (intakeText: string) => Promise<void>;
  disabled?: boolean;
}

export function StartSurface({ onStart, disabled = false }: StartSurfaceProps) {
  const [intakeText, setIntakeText] = useState("");
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (inFlight || disabled) return;
    const text = intakeText.trim();
    if (!text) {
      setError("Please provide a short summary, background, or notes to begin.");
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
    <section className="start-surface" aria-labelledby="start-heading">
      <div className="start-header">
        <p className="eyebrow">OryxenAI / Portfolio Studio</p>
        <h1 id="start-heading">Let's find the story your portfolio should tell.</h1>
        <p className="start-thesis">
          Turn your experience into a deliberate, verified portfolio through five specialized stages:
          Discover, Content, Design, Prepare, and Generate.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="start-form">
        <label htmlFor="intake-notes" className="start-label">
          Your background, bio, or project notes
        </label>
        <textarea
          id="intake-notes"
          className="start-textarea"
          rows={6}
          placeholder="Paste anything you have: a bio, rough resume bullets, recent projects, or what you want people to know about your work..."
          value={intakeText}
          onInput={(e) => {
            setIntakeText((e.target as HTMLTextAreaElement).value);
            if (error) setError(null);
          }}
          disabled={inFlight || disabled}
        />

        {error && <p className="start-error" role="alert">{error}</p>}

        <div className="start-actions">
          <button
            type="submit"
            className="btn-primary"
            disabled={inFlight || disabled || !intakeText.trim()}
          >
            {inFlight ? "Starting portfolio..." : "Start my portfolio"}
          </button>
        </div>

        <p className="start-trust-note">
          <small>
            Your input is kept private. Nothing is published automatically — you review and approve each stage before continuing.
          </small>
        </p>
      </form>
    </section>
  );
}
