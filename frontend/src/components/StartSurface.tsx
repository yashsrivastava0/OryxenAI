import { useMemo, useState } from "preact/hooks";

export interface StartSurfaceProps {
  onStart: (intakeText: string) => Promise<void>;
  disabled?: boolean;
  disabledReason?: string;
}

const PROMPTS = [
  "The work I want to be known for",
  "Two projects worth examining",
  "The audience this portfolio must persuade",
  "Constraints, gaps, or claims to avoid",
];

export function StartSurface({ onStart, disabled = false, disabledReason }: StartSurfaceProps) {
  const [intakeText, setIntakeText] = useState("");
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const characterCount = useMemo(() => intakeText.trim().length, [intakeText]);

  const addPrompt = (prompt: string) => {
    setIntakeText((current) => `${current.trim()}${current.trim() ? "\n\n" : ""}${prompt}:\n`);
    setError(null);
  };

  const submit = async (event?: Event) => {
    event?.preventDefault();
    if (disabled || inFlight) return;
    const value = intakeText.trim();
    if (!value) {
      setError("Add a few factual notes, project details, or links before starting Discovery.");
      return;
    }
    setInFlight(true);
    setError(null);
    try {
      await onStart(value);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Discovery could not start. Try again.");
    } finally {
      setInFlight(false);
    }
  };

  return (
    <section className="start-surface" aria-labelledby="start-heading">
      <div className="start-hero-header">
        <p className="eyebrow">Portfolio studio / Discovery</p>
        <h1 id="start-heading">Shape the evidence. Approve the story.</h1>
        <p className="start-lede">
          Paste your resume, work history, or project notes below. Discovery extracts the signal, asks for what is missing, and never advances without your approval.
        </p>
      </div>

      <form className="intake-proof centered-composer" onSubmit={submit} noValidate>
        <div className="intake-heading">
          <label htmlFor="intake-notes">Source notes or resume</label>
          <span aria-label={`${characterCount} characters`}>{characterCount.toLocaleString()} characters</span>
        </div>
        <textarea
          id="intake-notes"
          rows={11}
          value={intakeText}
          placeholder="Paste your resume, work history, key project metrics, case study notes, or target roles here…"
          onInput={(event) => {
            setIntakeText((event.target as HTMLTextAreaElement).value);
            setError(null);
          }}
          onKeyDown={(event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") void submit(event);
          }}
          disabled={disabled || inFlight}
        />
        <div className="prompt-notes" aria-label="Optional writing prompts">
          {PROMPTS.map((prompt) => (
            <button key={prompt} type="button" onClick={() => addPrompt(prompt)} disabled={disabled || inFlight}>
              + {prompt}
            </button>
          ))}
        </div>
        {error ? <p className="start-error" role="alert">{error}</p> : null}
        {disabledReason ? <p className="start-error" role="alert">{disabledReason}</p> : null}
        <div className="intake-actions">
          <p>🔒 Private workspace · Explicit approval at each stage</p>
          <button className="btn-primary" type="submit" disabled={disabled || inFlight || !intakeText.trim()}>
            {inFlight ? "Starting Discovery…" : "Start Discovery →"}
          </button>
        </div>
      </form>

      <div className="start-method-banner" aria-label="Three-stage workflow">
        <div className="method-step">
          <span className="step-num">01</span>
          <div className="step-text"><strong>Discovery</strong><small>signal & brief</small></div>
        </div>
        <span className="method-sep" aria-hidden="true">→</span>
        <div className="method-step">
          <span className="step-num">02</span>
          <div className="step-text"><strong>Content</strong><small>routes & copy</small></div>
        </div>
        <span className="method-sep" aria-hidden="true">→</span>
        <div className="method-step">
          <span className="step-num">03</span>
          <div className="step-text"><strong>Direction</strong><small>visual systems</small></div>
        </div>
      </div>
    </section>
  );
}
