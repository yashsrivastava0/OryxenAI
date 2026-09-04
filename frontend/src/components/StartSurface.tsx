import { useMemo, useState } from "preact/hooks";

export interface StartSurfaceProps {
  onStart: (intakeText: string) => Promise<void>;
  disabled?: boolean;
}

const PROMPTS = [
  "The work I want to be known for",
  "Two projects worth examining",
  "The audience this portfolio must persuade",
  "Constraints, gaps, or claims to avoid",
];

export function StartSurface({ onStart, disabled = false }: StartSurfaceProps) {
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
      <div className="start-editorial">
        <p className="eyebrow">First proof / Discovery</p>
        <h2 id="start-heading">Begin with evidence, not a template.</h2>
        <p className="start-lede">
          Paste the material you already trust: a short bio, resume bullets, project notes, links, or the role this portfolio should support. Discovery will ask only for what is missing.
        </p>
        <ol className="start-method" aria-label="Three-stage workflow">
          <li><span>01</span><strong>Discovery</strong><small>find the signal in your experience</small></li>
          <li><span>02</span><strong>Content</strong><small>shape routes and portfolio copy</small></li>
          <li><span>03</span><strong>Direction</strong><small>approve a coherent visual system</small></li>
        </ol>
      </div>

      <form className="intake-proof" onSubmit={submit} noValidate>
        <div className="intake-heading">
          <label htmlFor="intake-notes">Source notes</label>
          <span aria-label={`${characterCount} characters`}>{characterCount.toLocaleString()} characters</span>
        </div>
        <textarea
          id="intake-notes"
          rows={12}
          value={intakeText}
          placeholder="Example: I design reliable backend systems. The strongest evidence is a queue migration I led, an API platform I rebuilt, and the way I mentor engineers..."
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
        <div className="intake-actions">
          <p>Your notes stay private. Each stage waits for your explicit approval.</p>
          <button className="btn-primary" type="submit" disabled={disabled || inFlight || !intakeText.trim()}>
            {inFlight ? "Starting Discovery…" : "Start Discovery"}
          </button>
        </div>
      </form>
    </section>
  );
}
