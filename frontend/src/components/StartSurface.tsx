import { useMemo, useState, useRef, useEffect } from "preact/hooks";
import { safeSessionStorage } from "../data/safe-storage";

export interface StartSurfaceProps {
  onStart: (intakeText: string) => Promise<void>;
  disabled?: boolean;
  disabledReason?: string;
  continuation?: boolean;
}

interface StarterPrompt {
  id: string;
  text: string;
}

const STARTER_PROMPTS: StarterPrompt[] = [
  {
    id: "portfolio_goal",
    text: "I want a portfolio that helps people understand...",
  },
  {
    id: "work_to_highlight",
    text: "The work and projects I want to highlight include...",
  },
  {
    id: "constraints_preferences",
    text: "My audience, preferences, or constraints are...",
  },
];

export function StartSurface({
  onStart,
  disabled = false,
  disabledReason,
  continuation = false,
}: StartSurfaceProps) {
  const [intakeText, setIntakeText] = useState(() => safeSessionStorage.getItem("oryxenai.discovery_intake_draft") ?? "");
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    safeSessionStorage.setItem("oryxenai.discovery_intake_draft", intakeText);
  }, [intakeText]);

  const wordCount = useMemo(() => {
    const trimmed = intakeText.trim();
    return trimmed ? trimmed.split(/\s+/).length : 0;
  }, [intakeText]);

  const handleSelectPrompt = (promptText: string) => {
    setIntakeText((prev) => {
      const next = prev.trim() ? `${prev}\n\n${promptText}` : promptText;
      return next;
    });
    setError(null);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const submit = async (event?: Event) => {
    event?.preventDefault();
    if (disabled || inFlight) return;
    const value = intakeText.trim();
    if (!value) {
      setError("Please share your goals, context, or paste your resume before starting Discovery.");
      return;
    }
    setInFlight(true);
    setError(null);
    try {
      await onStart(value);
      safeSessionStorage.removeItem("oryxenai.discovery_intake_draft");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Discovery could not start. Try again.");
    } finally {
      setInFlight(false);
    }
  };

  return (
    <div className="discovery-intake-surface" aria-labelledby="intake-heading">
      {/* Editorial Header matching 02-discovery-intake.png */}
      <div className="discovery-intake-header">
        <h1 id="intake-heading" className="discovery-intake-title">
          {continuation ? "Share more source material." : "Give Discovery the full picture."}
        </h1>
        <p className="discovery-intake-subtitle">
          {continuation
            ? "Discovery needs more personal or professional detail before it can make a grounded brief. Add notes, work history, project details, or other source material below. Your earlier material is saved."
            : "Share your goals, work history, projects, preferences, and constraints. You can paste source material as-is; Discovery will organize it and ask about important gaps."}
        </p>
      </div>

      {/* Main Textarea Container with Word Count inside */}
      <div className={`discovery-intake-box ${isFocused ? "is-focused" : ""} ${error ? "has-error" : ""}`}>
        <label htmlFor="discovery-intake-textarea" className="visually-hidden">
          Source material and portfolio goals
        </label>
        <textarea
          ref={textareaRef}
          id="discovery-intake-textarea"
          className="discovery-intake-textarea"
          placeholder="Write your goals or paste resumes, project notes, work history, and other relevant material..."
          value={intakeText}
          onInput={(e) => {
            setIntakeText((e.target as HTMLTextAreaElement).value);
            if (error) setError(null);
          }}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          disabled={disabled || inFlight}
          rows={8}
        />
        <div className="discovery-intake-meta">
          {error && <span className="discovery-intake-error" role="alert">{error}</span>}
          <span className="discovery-intake-counter">{wordCount.toLocaleString()} words</span>
        </div>
      </div>

      {/* Starting point suggestion cards matching 02-discovery-intake.png */}
      <div className="discovery-starting-points">
        <div className="starting-points-header">
          <h2>Need a starting point?</h2>
          <p>Try one of these prompts or write your own.</p>
        </div>
        <div className="starting-points-grid">
          {STARTER_PROMPTS.map((prompt) => (
            <button
              key={prompt.id}
              type="button"
              className="starter-prompt-card"
              onClick={() => handleSelectPrompt(prompt.text)}
              disabled={disabled || inFlight}
            >
              <span className="starter-prompt-text">{prompt.text}</span>
              <span className="starter-prompt-arrow" aria-hidden="true">→</span>
            </button>
          ))}
        </div>
      </div>

      {disabledReason && (
        <div className="discovery-disabled-notice" role="alert">
          {disabledReason}
        </div>
      )}

      <p className="intake-supporting-note">
        {continuation
          ? "Add the details you have; Discovery will keep the new material with your earlier sources."
          : "Start with what you have. You can clarify gaps and review the evidence before approving the brief."}
      </p>

      {/* Reserved action area matching 02-discovery-intake.png; intake keeps
          this dock in normal flow so the prompt deck is never obscured. */}
      <div className="action-dock intake-dock">
        <div className="action-dock-content">
          <div className="action-dock-right">
            <div className="dock-button-wrapper">
              <button
                type="button"
                className="btn-primary btn-cobalt"
                onClick={submit}
                disabled={disabled || inFlight || !intakeText.trim()}
              >
                {inFlight
                  ? continuation ? "Adding details…" : "Starting Discovery…"
                  : continuation ? "Add details and continue →" : "Start Discovery →"}
              </button>
              <span className="dock-reassurance">Long source material is accepted; the server will report any transport limit.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
