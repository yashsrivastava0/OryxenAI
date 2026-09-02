import { useState, useEffect, useRef } from "preact/hooks";
import { safeSessionStorage } from "../data/safe-storage";

export interface RevisionComposerProps {
  artifactName: string; // e.g. "brief", "content plan", "visual direction"
  onSubmit: (revisionRequest: string) => Promise<void>;
  onCancel: () => void;
  disabled?: boolean;
}

export function RevisionComposer({
  artifactName,
  onSubmit,
  onCancel,
  disabled = false,
}: RevisionComposerProps) {
  const draftKey = `oryxenai.revision_draft.${artifactName.replace(/\s+/g, "_")}`;
  const [requestText, setRequestText] = useState("");
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const saved = safeSessionStorage.getItem(draftKey);
    if (saved) setRequestText(saved);
    if (textareaRef.current) textareaRef.current.focus();
  }, [draftKey]);

  const handleChange = (value: string) => {
    setRequestText(value);
    safeSessionStorage.setItem(draftKey, value);
    if (error) setError(null);
  };

  const handleSubmit = async (e?: Event) => {
    if (e) e.preventDefault();
    if (inFlight || disabled) return;
    const text = requestText.trim();
    if (!text) {
      setError("Please describe the adjustments or revisions you would like made.");
      return;
    }

    setInFlight(true);
    setError(null);
    try {
      await onSubmit(text);
      safeSessionStorage.removeItem(draftKey);
      setRequestText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revision request failed. Please try again.");
    } finally {
      setInFlight(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="revision-composer" role="region" aria-label={`Revise ${artifactName}`}>
      <div className="revision-header">
        <h3>Request changes to this {artifactName}</h3>
        <p className="revision-explanation">
          Describe what you would like adjusted. The stage will rebuild this draft according to your instructions.
        </p>
      </div>

      <textarea
        ref={textareaRef}
        className="revision-textarea"
        rows={4}
        placeholder={`e.g. Make the positioning punchier, emphasize distributed systems, and condense secondary sections...`}
        value={requestText}
        onInput={(e) => handleChange((e.target as HTMLTextAreaElement).value)}
        onKeyDown={handleKeyDown}
        disabled={inFlight || disabled}
      />

      {error && <p className="revision-error" role="alert">{error}</p>}

      <div className="revision-actions">
        <button
          type="button"
          className="btn-primary"
          disabled={inFlight || disabled || !requestText.trim()}
          onClick={() => handleSubmit()}
        >
          {inFlight ? "Sending revision..." : "Submit revision"}
        </button>
        <button
          type="button"
          className="btn-secondary"
          disabled={inFlight}
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
