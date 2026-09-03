import { useState, useEffect, useRef } from "preact/hooks";
import type { DiscoveryQuestionVM } from "../data/adapters/discovery";
import { safeSessionStorage } from "../data/safe-storage";

export interface AnsweredTurn {
  questionId: string;
  questionText: string;
  answerText: string;
}

export interface ConversationSurfaceProps {
  questions: DiscoveryQuestionVM[];
  history: AnsweredTurn[];
  isWorking: boolean;
  workingLabel?: string;
  disabled?: boolean;
  onSubmitAnswer: (questionId: string, mode: string, value: unknown, isComplete: boolean) => Promise<void>;
  onGenerateBriefNow?: () => Promise<void>;
}

export function ConversationSurface({
  questions,
  history,
  isWorking,
  workingLabel = "Analyzing your details...",
  disabled = false,
  onSubmitAnswer,
  onGenerateBriefNow,
}: ConversationSurfaceProps) {
  const currentQuestion = questions[0] ?? null;

  const [textAnswer, setTextAnswer] = useState("");
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const draftKey = currentQuestion ? `oryxenai.draft.${currentQuestion.id}` : null;
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  // Restore draft when current question changes
  useEffect(() => {
    if (draftKey) {
      const saved = safeSessionStorage.getItem(draftKey);
      if (saved) setTextAnswer(saved);
      else setTextAnswer("");
      setSelectedOptions([]);
      setError(null);
    }
  }, [draftKey]);

  const handleTextChange = (value: string) => {
    setTextAnswer(value);
    if (draftKey) {
      safeSessionStorage.setItem(draftKey, value);
    }
  };

  const handleClearDraft = () => {
    if (draftKey) safeSessionStorage.removeItem(draftKey);
    setTextAnswer("");
    setSelectedOptions([]);
  };

  const handleTextSubmit = async () => {
    if (!currentQuestion || inFlight || disabled) return;
    const trimmed = textAnswer.trim();
    if (!trimmed) return;

    setInFlight(true);
    setError(null);
    try {
      const isLast = questions.length <= 1;
      await onSubmitAnswer(currentQuestion.id, "text", trimmed, isLast);
      handleClearDraft();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your answer. Please try again.");
    } finally {
      setInFlight(false);
    }
  };

  const handleSingleSelect = async (optionId: string) => {
    if (!currentQuestion || inFlight || disabled) return;
    setInFlight(true);
    setError(null);
    try {
      const isLast = questions.length <= 1;
      await onSubmitAnswer(currentQuestion.id, "single_select", optionId, isLast);
      handleClearDraft();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your choice.");
    } finally {
      setInFlight(false);
    }
  };

  const handleBooleanSelect = async (val: boolean) => {
    if (!currentQuestion || inFlight || disabled) return;
    setInFlight(true);
    setError(null);
    try {
      const isLast = questions.length <= 1;
      await onSubmitAnswer(currentQuestion.id, "boolean", val ? "true" : "false", isLast);
      handleClearDraft();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your choice.");
    } finally {
      setInFlight(false);
    }
  };

  const handleMultiSelectSubmit = async () => {
    if (!currentQuestion || inFlight || disabled) return;
    if (!selectedOptions.length) return;
    setInFlight(true);
    setError(null);
    try {
      const isLast = questions.length <= 1;
      await onSubmitAnswer(currentQuestion.id, "multi_select", selectedOptions, isLast);
      handleClearDraft();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your selections.");
    } finally {
      setInFlight(false);
    }
  };

  const handleSkip = async () => {
    if (!currentQuestion || inFlight || disabled) return;
    setInFlight(true);
    setError(null);
    try {
      const isLast = questions.length <= 1;
      await onSubmitAnswer(currentQuestion.id, "skip", "", isLast);
      handleClearDraft();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not skip question.");
    } finally {
      setInFlight(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleTextSubmit();
    }
  };

  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!isWorking) {
      setElapsedSeconds(0);
      return;
    }
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [isWorking]);

  return (
    <section className="conversation-surface" aria-label="Discovery conversation">
      {/* Transcript of prior answered turns */}
      {history.length > 0 && (
        <div className="transcript-flow" aria-label="Previous answers">
          {history.map((turn, idx) => (
            <div key={idx} className="transcript-turn">
              <div className="transcript-bubble assistant">
                <p className="turn-label">Discovery</p>
                <p className="turn-text">{turn.questionText}</p>
              </div>
              <div className="transcript-bubble user">
                <p className="turn-label">You</p>
                <p className="turn-text">{turn.answerText}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Active working state */}
      {isWorking && (
        <div className="discovery-engine-monitor" role="status" aria-live="polite">
          <div className="engine-monitor-header">
            <div className="engine-status-badge">
              <span className="engine-beacon-dot" aria-hidden="true" />
              <span className="engine-badge-text">DISCOVERY ENGINE ACTIVE</span>
            </div>
            <span className="engine-elapsed-timer">
              {elapsedSeconds}s elapsed
            </span>
          </div>

          <h2 className="engine-monitor-title">{workingLabel}</h2>
          <p className="engine-monitor-desc">
            The Discovery agent is analyzing your background materials and synthesizing your portfolio direction.
          </p>

          <ol className="engine-milestones-track" role="list">
            <li className="engine-milestone complete">
              <span className="milestone-icon">✓</span>
              <span>Intake notes received</span>
            </li>
            <li className="engine-milestone active">
              <span className="milestone-pulse" />
              <span>Analyzing background & milestones</span>
            </li>
            <li className="engine-milestone pending">
              <span className="milestone-dot" />
              <span>Structuring portfolio brief</span>
            </li>
          </ol>

          <p className="engine-leave-reassurance">
            Work continues durably on the background server. You can safely stay on this page while it completes.
          </p>
        </div>
      )}

      {/* Actionable current question */}
      {!isWorking && currentQuestion && (
        <div className="active-question-card" aria-live="polite">
          <p className="eyebrow">Discovery Question</p>
          <h2 className="question-prompt">{currentQuestion.text}</h2>
          {currentQuestion.helpText && (
            <p className="question-help">{currentQuestion.helpText}</p>
          )}

          {error && <p className="question-error" role="alert">{error}</p>}

          {/* Question Kind: Single Select */}
          {currentQuestion.kind === "single_select" && (
            <div className="options-grid">
              {currentQuestion.options.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  className="btn-choice"
                  disabled={inFlight || disabled}
                  onClick={() => handleSingleSelect(opt.id)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          {/* Question Kind: Boolean */}
          {currentQuestion.kind === "boolean" && (
            <div className="options-grid boolean-grid">
              <button
                type="button"
                className="btn-choice"
                disabled={inFlight || disabled}
                onClick={() => handleBooleanSelect(true)}
              >
                Yes
              </button>
              <button
                type="button"
                className="btn-choice"
                disabled={inFlight || disabled}
                onClick={() => handleBooleanSelect(false)}
              >
                No
              </button>
            </div>
          )}

          {/* Question Kind: Multi Select */}
          {currentQuestion.kind === "multi_select" && (
            <div className="multi-select-form">
              <div className="checkbox-list">
                {currentQuestion.options.map((opt) => {
                  const checked = selectedOptions.includes(opt.id);
                  return (
                    <label key={opt.id} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={inFlight || disabled}
                        onChange={(e) => {
                          const isChecked = (e.target as HTMLInputElement).checked;
                          setSelectedOptions((prev) =>
                            isChecked ? [...prev, opt.id] : prev.filter((id) => id !== opt.id),
                          );
                        }}
                      />
                      <span>{opt.label}</span>
                    </label>
                  );
                })}
              </div>
              <div className="question-actions">
                <button
                  type="button"
                  className="btn-primary"
                  disabled={inFlight || disabled || !selectedOptions.length}
                  onClick={handleMultiSelectSubmit}
                >
                  {inFlight ? "Saving..." : "Save answer"}
                </button>
              </div>
            </div>
          )}

          {/* Question Kind: Text */}
          {currentQuestion.kind === "text" && (
            <div className="text-composer">
              <textarea
                ref={composerRef}
                className="composer-textarea"
                rows={4}
                placeholder="Type your answer here... (Ctrl+Enter to send)"
                value={textAnswer}
                onInput={(e) => handleTextChange((e.target as HTMLTextAreaElement).value)}
                onKeyDown={handleKeyDown}
                disabled={inFlight || disabled}
              />
              <div className="question-actions">
                <button
                  type="button"
                  className="btn-primary"
                  disabled={inFlight || disabled || !textAnswer.trim()}
                  onClick={handleTextSubmit}
                >
                  {inFlight ? "Saving..." : "Save and continue"}
                </button>
                {currentQuestion.allowSkip && (
                  <button
                    type="button"
                    className="btn-quiet"
                    disabled={inFlight || disabled}
                    onClick={handleSkip}
                  >
                    Skip question
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* If all questions answered and brief can be generated */}
      {!isWorking && !currentQuestion && onGenerateBriefNow && (
        <div className="ready-for-brief-card">
          <p className="eyebrow">Discovery Complete</p>
          <h2>We have enough detail to shape your brief.</h2>
          <p className="ready-thesis">
            Discovery is ready to synthesize your answers into a coherent portfolio brief.
          </p>
          <button
            type="button"
            className="btn-primary"
            disabled={inFlight || disabled}
            onClick={async () => {
              setInFlight(true);
              try {
                await onGenerateBriefNow();
              } finally {
                setInFlight(false);
              }
            }}
          >
            {inFlight ? "Creating brief..." : "Create my brief"}
          </button>
        </div>
      )}
    </section>
  );
}
