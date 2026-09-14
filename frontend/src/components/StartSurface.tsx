import { useMemo, useState, useRef, useEffect } from "preact/hooks";
import { safeSessionStorage } from "../data/safe-storage";

export interface StartSurfaceProps {
  onStart: (intakeText: string) => Promise<void>;
  disabled?: boolean;
  disabledReason?: string;
}

interface StarterPrompt {
  id: string;
  text: string;
}

const STARTER_PROMPTS: StarterPrompt[] = [
  {
    id: "product_opportunity",
    text: "Help me explore a new product opportunity in an adjacent market.",
  },
  {
    id: "simplify_workflow",
    text: "I want to simplify an existing workflow with AI.",
  },
  {
    id: "business_model",
    text: "Assess the viability of a new business model.",
  },
];

// This is guidance for a thorough source packet, not the transport safety
// limit. The backend contract remains bounded by the 30,000-character guard.
const MAX_INTAKE_WORDS = 3000;
const MAX_INTAKE_CHARACTERS = 30000;

export function StartSurface({ onStart, disabled = false, disabledReason }: StartSurfaceProps) {
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
    if (value.length > MAX_INTAKE_CHARACTERS) {
      setError(`Keep your source material under ${MAX_INTAKE_CHARACTERS.toLocaleString()} characters.`);
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
          Tell us about what you're exploring.
        </h1>
        <p className="discovery-intake-subtitle">
          Share your goals, context, and any constraints. The more detail you provide, the better
          OryxenAI can understand your needs and create a focused plan.
        </p>
      </div>

      {/* Main Textarea Container with Word Count inside */}
      <div className={`discovery-intake-box ${isFocused ? "is-focused" : ""} ${error ? "has-error" : ""}`}>
        <label htmlFor="discovery-intake-textarea" className="visually-hidden">
          What should this portfolio make clear?
        </label>
        <textarea
          ref={textareaRef}
          id="discovery-intake-textarea"
          className="discovery-intake-textarea"
          placeholder="Type your response here... (or paste your resume, work history, or project notes)"
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
          <span className={`discovery-intake-counter ${wordCount > MAX_INTAKE_WORDS ? "over-limit" : ""}`}>
            {wordCount.toLocaleString()} / {MAX_INTAKE_WORDS.toLocaleString()} words
          </span>
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
        Start with what you have. You can refine the brief before moving to Content.
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
                {inFlight ? "Starting Discovery…" : "Start Discovery →"}
              </button>
              <span className="dock-reassurance">Your input is private and secure.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
