import { useState, useEffect, useRef } from "preact/hooks";
import type { DiscoveryQuestionVM } from "../data/adapters/discovery";
import type { StageJobViewModel } from "../data/adapters/job";
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
  job?: StageJobViewModel | null;
  workingLabel?: string;
  disabled?: boolean;
  onSubmitAnswer: (questionId: string, mode: string, value: unknown, isComplete: boolean) => Promise<void>;
  onGenerateBriefNow?: () => Promise<void>;
  onRetryStalled?: () => Promise<void>;
  onStop?: () => Promise<void>;
}

export function ConversationSurface({
  questions,
  history,
  isWorking,
  job,
  workingLabel = "Discovery is processing your saved material",
  disabled = false,
  onSubmitAnswer,
  onGenerateBriefNow,
  onRetryStalled,
  onStop,
}: ConversationSurfaceProps) {
  const currentQuestion = questions[0] ?? null;

  const [textAnswer, setTextAnswer] = useState("");
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [inFlight, setInFlight] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());

  const draftKey = currentQuestion ? `oryxenai.draft.${currentQuestion.id}` : null;
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!isWorking) return;
    setNowMs(Date.now());
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [isWorking]);

  const jobCreatedMs = job?.createdAt ? Date.parse(job.createdAt) : Number.NaN;
  const jobHeartbeatMs = job?.heartbeatAt ? Date.parse(job.heartbeatAt) : Number.NaN;
  const queuedAgeSeconds = Number.isFinite(jobCreatedMs) ? Math.max(0, (nowMs - jobCreatedMs) / 1000) : null;
  const heartbeatAgeSeconds = Number.isFinite(jobHeartbeatMs) ? Math.max(0, (nowMs - jobHeartbeatMs) / 1000) : null;
  const workerStalled = Boolean(
    isWorking &&
      ((job?.status === "queued" && queuedAgeSeconds !== null && queuedAgeSeconds >= 20) ||
        (job?.status === "running" && heartbeatAgeSeconds !== null && heartbeatAgeSeconds >= 180)),
  );

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return "a moment";
    if (seconds < 60) return `${Math.max(1, Math.floor(seconds))} seconds`;
    return `${Math.floor(seconds / 60)} minutes`;
  };

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

  const handleStop = async () => {
    if (!onStop || stopping || disabled) return;
    setStopping(true);
    setError(null);
    try {
      await onStop();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not stop Discovery.");
    } finally {
      setStopping(false);
    }
  };

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
        <div className={`agent-working-proof${workerStalled ? " worker-stalled" : ""}`} role="status" aria-live="polite" aria-busy={!workerStalled}>
          <p className="eyebrow">Discovery / {workerStalled ? "worker check" : "in progress"}</p>
          <h2>{workerStalled ? "Discovery is waiting for the worker" : workingLabel}</h2>
          <div className="working-rule" aria-hidden="true"><span /></div>
          {workerStalled ? (
            <>
              <p>
                Your notes are saved. This run has been {job?.status === "queued" ? "queued" : "running"} for {formatDuration(job?.status === "queued" ? queuedAgeSeconds : heartbeatAgeSeconds)}, but the worker has not acknowledged a recent update.
              </p>
              <div className="question-actions">
                <button type="button" className="btn-secondary" onClick={() => void onRetryStalled?.()} disabled={disabled || stopping || !onRetryStalled}>
                  Check again
                </button>
                {onStop ? <button type="button" className="btn-quiet stop-action" onClick={() => void handleStop()} disabled={disabled || stopping}>{stopping ? "Stopping..." : "Stop Discovery"}</button> : null}
              </div>
            </>
          ) : (
            <>
              <p>The server has your input. You may leave this page; the durable job continues and this proof will update when its state changes.</p>
              {onStop ? <div className="question-actions"><button type="button" className="btn-quiet stop-action" onClick={() => void handleStop()} disabled={disabled || stopping}>{stopping ? "Stopping..." : "Stop Discovery"}</button></div> : null}
            </>
          )}
        </div>
      )}

      {/* Actionable current question */}
      {!isWorking && currentQuestion && (
        <div className="active-question-card" aria-live="polite">
          <p className="eyebrow">Discovery / next question</p>
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
                placeholder="Add the detail that would make this answer accurate…"
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
          <p className="eyebrow">Discovery / answers saved</p>
          <h2>We have enough detail to shape your brief.</h2>
          <p className="ready-thesis">
            Discovery is ready to synthesize your answers into a coherent portfolio brief.
          </p>
          {error && <p className="question-error" role="alert">{error}</p>}
          <button
            type="button"
            className="btn-primary"
            disabled={inFlight || disabled}
            onClick={async () => {
              setInFlight(true);
              setError(null);
              try {
                await onGenerateBriefNow();
              } catch (reason) {
                setError(reason instanceof Error ? reason.message : "The brief could not be started. Try again.");
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
