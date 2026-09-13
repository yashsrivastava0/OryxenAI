import { useMemo, useState, useRef, useEffect } from "preact/hooks";
import { safeSessionStorage } from "../data/safe-storage";

export interface StartSurfaceProps {
  onStart: (intakeText: string) => Promise<void>;
  disabled?: boolean;
  disabledReason?: string;
}

interface PromptDef {
  id: string;
  title: string;
  placeholder: string;
}

const SUPPORTING_PROMPTS: PromptDef[] = [
  {
    id: "known_for",
    title: "The work I want to be known for",
    placeholder: "Key skills, leadership scope, specialized craft, or signature achievements you want prioritized…",
  },
  {
    id: "projects",
    title: "Two projects worth examining",
    placeholder: "Name 1–2 standout projects, your exact contributions, key metrics, or technical hurdles solved…",
  },
  {
    id: "audience",
    title: "The audience this portfolio should reach",
    placeholder: "Hiring managers, executive clients, investors, or peer collaborators you aim to influence…",
  },
  {
    id: "constraints",
    title: "Constraints, gaps, or claims to avoid",
    placeholder: "Confidential aspects, skills you don't want to repeat, career gaps, or claims to downplay…",
  },
];

const MAX_INTAKE_CHARACTERS = 30000;

export function StartSurface({ onStart, disabled = false, disabledReason }: StartSurfaceProps) {
  const [intakeText, setIntakeText] = useState(() => safeSessionStorage.getItem("oryxenai.discovery_intake_draft") ?? "");
  const [promptValues, setPromptValues] = useState<Record<string, string>>({});
  const [openPromptIds, setOpenPromptIds] = useState<Set<string>>(new Set());
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);
  const [pasteNotice, setPasteNotice] = useState<string | null>(null);
  const pasteTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (pasteTimerRef.current) window.clearTimeout(pasteTimerRef.current);
    };
  }, []);

  useEffect(() => {
    safeSessionStorage.setItem("oryxenai.discovery_intake_draft", intakeText);
  }, [intakeText]);

  const totalContent = useMemo(() => {
    let combined = intakeText.trim();
    for (const prompt of SUPPORTING_PROMPTS) {
      const val = (promptValues[prompt.id] || "").trim();
      if (val) {
        combined += (combined ? "\n\n" : "") + `[${prompt.title}]:\n${val}`;
      }
    }
    return combined;
  }, [intakeText, promptValues]);

  const characterCount = useMemo(() => totalContent.length, [totalContent]);
  const wordCount = useMemo(() => {
    const trimmed = totalContent.trim();
    return trimmed ? trimmed.split(/\s+/).length : 0;
  }, [totalContent]);

  const togglePrompt = (id: string) => {
    setOpenPromptIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const updatePromptValue = (id: string, val: string) => {
    setPromptValues((prev) => ({ ...prev, [id]: val }));
    setError(null);
  };

  const handlePaste = () => {
    setPasteNotice("Source added");
    if (pasteTimerRef.current) window.clearTimeout(pasteTimerRef.current);
    pasteTimerRef.current = window.setTimeout(() => {
      setPasteNotice(null);
    }, 1800);
  };

  const submit = async (event?: Event) => {
    event?.preventDefault();
    if (disabled || inFlight) return;
    const value = totalContent.trim();
    if (!value) {
      setError("Add your resume, work history, or project notes before starting Discovery.");
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

  const statusChipText = pasteNotice
    ? pasteNotice
    : isFocused
      ? "Draft active"
      : characterCount > 0
        ? "Ready to structure your brief"
        : "Ready to structure your brief";

  return (
    <section className="start-surface" aria-labelledby="start-heading">
      {/* Compact editorial introduction */}
      <div className="start-hero-header">
        <p className="eyebrow">PORTFOLIO STUDIO / DISCOVERY</p>
        <h1 id="start-heading">Bring your work into focus.</h1>
        <p className="start-lede">
          Paste your resume, work history, or project notes. Discovery pulls out what matters, spots the gaps, and asks for approval before moving on.
        </p>
      </div>

      {/* Main Discovery Workbench Card */}
      <div className={`discovery-workbench-card ${isFocused ? "is-focused" : ""}`}>
        <div className="workbench-top-rule" aria-hidden="true">
          <span className="workbench-sweep" />
        </div>

        <form className="workbench-form" onSubmit={submit} noValidate>
          {/* Workbench Header */}
          <div className="workbench-header">
            <label className="workbench-label" htmlFor="intake-notes">
              What should this portfolio make clear?
            </label>
            <div className="workbench-meta">
              <span className={`status-chip ${pasteNotice ? "chip-notice" : isFocused ? "chip-active" : "chip-ready"}`} aria-live="polite">
                <span className="status-dot" aria-hidden="true" />
                {statusChipText}
              </span>
              <span className="count-metrics" aria-label={`${wordCount} words, ${characterCount} characters`}>
                {wordCount} words · {characterCount} characters
              </span>
            </div>
          </div>

          {/* Primary Textarea */}
          <div className="textarea-container">
            <textarea
              id="intake-notes"
              className="workbench-textarea"
              rows={5}
              maxLength={MAX_INTAKE_CHARACTERS}
              value={intakeText}
              placeholder="Paste your resume, work history, key project metrics, case study notes, or target roles here…"
              onInput={(event) => {
                setIntakeText((event.target as HTMLTextAreaElement).value.slice(0, MAX_INTAKE_CHARACTERS));
                setError(null);
              }}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onPaste={handlePaste}
              onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === "Enter") void submit(event);
              }}
              disabled={disabled || inFlight}
            />
          </div>

          {/* 4 Optional Disclosure Rows in 2x2 grid */}
          <div className="disclosure-grid" aria-label="Supporting writing prompts">
            {SUPPORTING_PROMPTS.map((prompt) => {
              const isOpen = openPromptIds.has(prompt.id);
              const val = promptValues[prompt.id] || "";
              return (
                <div key={prompt.id} className={`disclosure-item ${isOpen ? "open" : ""} ${val.trim() ? "has-content" : ""}`}>
                  <button
                    type="button"
                    className="disclosure-toggle"
                    aria-expanded={isOpen}
                    onClick={() => togglePrompt(prompt.id)}
                    disabled={disabled || inFlight}
                  >
                    <span className="toggle-symbol" aria-hidden="true">{isOpen ? "−" : "+"}</span>
                    <span className="toggle-title">{prompt.title}</span>
                    {val.trim() && !isOpen && <span className="content-indicator" title="Draft added">●</span>}
                  </button>

                  {isOpen && (
                    <div className="disclosure-body">
                      <textarea
                        className="disclosure-textarea"
                        rows={3}
                        placeholder={prompt.placeholder}
                        value={val}
                        onInput={(e) => updatePromptValue(prompt.id, (e.target as HTMLTextAreaElement).value)}
                        disabled={disabled || inFlight}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {error ? <p className="start-error" role="alert">{error}</p> : null}
          {disabledReason ? <p className="start-error" role="alert">{disabledReason}</p> : null}

          {/* Workbench Footer */}
          <div className="workbench-footer">
            <div className="privacy-reassurance">
              <span className="lock-icon" aria-hidden="true">🔒</span>
              <span>Private workspace · Nothing moves forward without your approval.</span>
            </div>

            <button
              className="btn-primary start-discovery-cta"
              type="submit"
              disabled={disabled || inFlight || !totalContent.trim()}
            >
              <span className="cta-label">{inFlight ? "Starting Discovery…" : "Start Discovery"}</span>
              {!inFlight && <span className="cta-arrow" aria-hidden="true">→</span>}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
