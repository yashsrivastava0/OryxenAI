import { useState, useEffect, useRef } from "preact/hooks";
import type { DiscoveryQuestionVM } from "../data/adapters/discovery";
import type { StageJobViewModel } from "../data/adapters/job";
import {
  answeredDiscoveryQuestion,
  skippedDiscoveryQuestion,
  type DiscoveryAnswerSubmission,
} from "../data/discovery-answer";
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
  onSubmitAnswer: (answer: DiscoveryAnswerSubmission, isComplete: boolean) => Promise<void>;
  onGenerateBriefNow?: () => Promise<void>;
  onRetryStalled?: () => Promise<void>;
  onStop?: () => Promise<void>;
}

export function ConversationSurface({
  questions,
  history,
  isWorking,
  job,
  workingLabel = "Reading your source material and deciding what to ask next",
  disabled = false,
  onSubmitAnswer,
  onGenerateBriefNow,
  onRetryStalled,
  onStop,
}: ConversationSurfaceProps) {
  const currentQuestion = questions[0] ?? null;

  const [textAnswer, setTextAnswer] = useState("");
  const [selectedSingleOption, setSelectedSingleOption] = useState<string | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [inFlight, setInFlight] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusAnnouncement, setStatusAnnouncement] = useState<string>("");
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

  const currentQuestionOrdinal = history.length + 1;
  const totalQuestionsInBatch = history.length + questions.length;
  const questionOrdinalText = `Question ${String(currentQuestionOrdinal).padStart(2, "0")}${
    totalQuestionsInBatch > 0 ? ` of ${String(totalQuestionsInBatch).padStart(2, "0")}` : ""
  }`;

  useEffect(() => {
    if (currentQuestion) {
      if (draftKey) {
        const saved = safeSessionStorage.getItem(draftKey);
        if (saved) setTextAnswer(saved);
        else setTextAnswer("");
      } else {
        setTextAnswer("");
      }
      setSelectedSingleOption(null);
      setSelectedOptions([]);
      setError(null);
      setStatusAnnouncement(`${questionOrdinalText}: ${currentQuestion.text}`);
    }
  }, [currentQuestion?.id, draftKey]);

  const handleTextChange = (value: string) => {
    setTextAnswer(value);
    if (draftKey) {
      safeSessionStorage.setItem(draftKey, value);
    }
  };

  const handleClearDraft = () => {
    if (draftKey) safeSessionStorage.removeItem(draftKey);
    setTextAnswer("");
    setSelectedSingleOption(null);
    setSelectedOptions([]);
  };

  const executeAnswer = async (fn: () => Promise<void>) => {
    if (typeof document !== "undefined" && "startViewTransition" in document) {
      (document as unknown as { startViewTransition: (cb: () => Promise<void>) => void }).startViewTransition(fn);
    } else {
      await fn();
    }
  };

  const isLast = questions.length <= 1;

  const handleTextSubmit = async () => {
    if (!currentQuestion || inFlight || disabled) return;
    const trimmed = textAnswer.trim();
    if (!trimmed) return;

    setInFlight(true);
    setError(null);
    try {
      await executeAnswer(async () => {
        await onSubmitAnswer(answeredDiscoveryQuestion(currentQuestion.id, trimmed), isLast);
        handleClearDraft();
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't save that answer. Try again.");
    } finally {
      setInFlight(false);
    }
  };

  const handleSingleSelect = (optionId: string) => {
    if (inFlight || disabled) return;
    setSelectedSingleOption(optionId);
  };

  const handleSingleSubmit = async () => {
    if (!currentQuestion || inFlight || disabled || !selectedSingleOption) return;
    setInFlight(true);
    setError(null);
    try {
      await executeAnswer(async () => {
        await onSubmitAnswer(answeredDiscoveryQuestion(currentQuestion.id, selectedSingleOption), isLast);
        handleClearDraft();
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't save that answer. Try again.");
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
      await executeAnswer(async () => {
        await onSubmitAnswer(answeredDiscoveryQuestion(currentQuestion.id, selectedOptions), isLast);
        handleClearDraft();
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't save that answer. Try again.");
    } finally {
      setInFlight(false);
    }
  };

  const handleSkip = async () => {
    if (!currentQuestion || inFlight || disabled) return;
    setInFlight(true);
    setError(null);
    try {
      await executeAnswer(async () => {
        await onSubmitAnswer(skippedDiscoveryQuestion(currentQuestion.id), isLast);
        handleClearDraft();
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't save that answer. Try again.");
    } finally {
      setInFlight(false);
    }
  };

  const isSubmitDisabled = (() => {
    if (inFlight || disabled) return true;
    if (!currentQuestion) return true;
    if (currentQuestion.kind === "text") return !textAnswer.trim();
    if (currentQuestion.kind === "multi_select") return selectedOptions.length === 0;
    if (currentQuestion.kind === "single_select" || currentQuestion.kind === "boolean") {
      return !selectedSingleOption;
    }
    return false;
  })();

  const handleSubmit = async () => {
    if (currentQuestion?.kind === "text") {
      await handleTextSubmit();
    } else if (currentQuestion?.kind === "multi_select") {
      await handleMultiSelectSubmit();
    } else if (currentQuestion?.kind === "single_select" || currentQuestion?.kind === "boolean") {
      await handleSingleSubmit();
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      void handleSubmit();
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

  const submitButtonLabel = inFlight ? "Saving answer…" : isLast ? "Submit answer" : "Next question";

  return (
    <section className="conversation-surface" aria-label="Discovery interview">
      {/* 1. Spatially Continuous Analysis State (when worker is processing) */}
      {isWorking && (
        <div
          className={`discovery-workbench-card working-workbench-card ${workerStalled ? "worker-stalled" : ""}`}
          role="status"
          aria-live="polite"
          aria-busy={!workerStalled}
        >
          <div className="workbench-top-rule" aria-hidden="true">
            <span className="workbench-sweep active-sweep" />
          </div>

          <div className="workbench-header">
            <span className="eyebrow">
              DISCOVERY / {workerStalled ? "WORKER CHECK" : "ANALYZING SOURCE"}
            </span>
            <span className="status-chip chip-active">
              <span className="status-dot pulsing" aria-hidden="true" />
              {workerStalled ? "Waiting for worker" : "Reading material"}
            </span>
          </div>

          <div className="working-body">
            <h2 className="working-headline">
              {workerStalled
                ? "Discovery is waiting for the background worker"
                : (workingLabel || "Reading your source material and deciding what to ask next.")}
            </h2>

            <div className="living-draft-activity-rail" aria-hidden="true">
              <div className="activity-step step-done">
                <span className="step-point">✓</span>
                <span className="step-text">Source received</span>
              </div>
              <span className="activity-connector active" />
              <div className="activity-step step-running">
                <span className="step-point">●</span>
                <span className="step-text">Understanding background & finding gaps</span>
              </div>
              <span className="activity-connector" />
              <div className="activity-step step-pending">
                <span className="step-point">○</span>
                <span className="step-text">Formulating focused questions</span>
              </div>
            </div>

            {workerStalled ? (
              <div className="stalled-callout">
                <p>
                  Your notes are safely saved. This job has been{" "}
                  {job?.status === "queued" ? "queued" : "running"} for{" "}
                  {formatDuration(job?.status === "queued" ? queuedAgeSeconds : heartbeatAgeSeconds)}, but
                  the worker has not reported recent progress.
                </p>
                <div className="question-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => void onRetryStalled?.()}
                    disabled={disabled || stopping || !onRetryStalled}
                  >
                    Check again
                  </button>
                  {onStop && (
                    <button
                      type="button"
                      className="btn-quiet stop-action"
                      onClick={() => void handleStop()}
                      disabled={disabled || stopping}
                    >
                      {stopping ? "Stopping..." : "Stop Discovery"}
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="working-note">
                <p>
                  The server has your material. You may leave or refresh this page; the background job
                  persists and this workbench will update as soon as questions are prepared.
                </p>
                {onStop && (
                  <div className="question-actions">
                    <button
                      type="button"
                      className="btn-quiet stop-action"
                      onClick={() => void handleStop()}
                      disabled={disabled || stopping}
                    >
                      {stopping ? "Stopping..." : "Stop Discovery"}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Status announcer for accessibility (polite announcement of new questions) */}
      <div className="visually-hidden" role="status" aria-live="polite" aria-atomic="true">
        {statusAnnouncement}
      </div>

      {/* 2. Compact Prior Answers Accordion */}
      {!isWorking && history.length > 0 && (
        <details className="prior-answers-accordion" aria-label="Earlier answers history">
          <summary className="prior-answers-summary">
            <span className="summary-chevron" aria-hidden="true">▶</span>
            <span className="prior-answers-title">Earlier answers</span>
            <span className="prior-answers-count">({history.length})</span>
          </summary>
          <div className="prior-answers-drawer">
            {history.map((turn, idx) => (
              <div key={idx} className="prior-answer-row">
                <div className="prior-question">
                  <span className="prior-label">Q{idx + 1}:</span>
                  <span className="prior-text">{turn.questionText}</span>
                </div>
                <div className="prior-response">
                  <span className="prior-label">Answer:</span>
                  <span className="prior-value">{turn.answerText}</span>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* 3. Actionable Focused Single-Question Card */}
      {!isWorking && currentQuestion && (
        <div className="discovery-workbench-card active-question-card">
          <div className="workbench-top-rule" aria-hidden="true">
            <span className="workbench-sweep" />
          </div>

          <div className="question-content">
            <div className="question-header">
              <div className="question-eyebrow-row">
                <span className="question-stage-tag">DISCOVERY</span>
                <span className="question-ordinal">{questionOrdinalText}</span>
              </div>
              <h2 className="question-prompt">{currentQuestion.text}</h2>
              {currentQuestion.helpText && (
                <p className="question-help">{currentQuestion.helpText}</p>
              )}
            </div>

            {error && (
              <div className="discovery-error-callout" role="alert">
                <span className="error-icon" aria-hidden="true">⚠</span>
                <span>{error}</span>
              </div>
            )}

            {/* Single Select */}
            {currentQuestion.kind === "single_select" && (
              <fieldset className="choice-fieldset">
                <legend className="choice-group-hint">SELECT ONE</legend>
                <div className="choice-list" role="radiogroup" aria-label={currentQuestion.text}>
                  {currentQuestion.options.map((opt) => {
                    const isSelected = selectedSingleOption === opt.id;
                    return (
                      <label
                        key={opt.id}
                        className={`choice-tile ${isSelected ? "is-selected" : ""}`}
                      >
                        <input
                          type="radio"
                          name={`discovery-q-${currentQuestion.id}`}
                          className="visually-hidden choice-input"
                          checked={isSelected}
                          disabled={inFlight || disabled}
                          onChange={() => handleSingleSelect(opt.id)}
                        />
                        <span className="choice-indicator choice-indicator--radio" aria-hidden="true">
                          {isSelected && <span className="choice-radio-dot" />}
                        </span>
                        <span className="choice-text">{opt.label}</span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            )}

            {/* Boolean */}
            {currentQuestion.kind === "boolean" && (
              <fieldset className="choice-fieldset">
                <legend className="choice-group-hint">SELECT ONE</legend>
                <div className="choice-list boolean-choice-list" role="radiogroup" aria-label={currentQuestion.text}>
                  {[
                    { id: "true", label: "Yes" },
                    { id: "false", label: "No" },
                  ].map((opt) => {
                    const isSelected = selectedSingleOption === opt.id;
                    return (
                      <label
                        key={opt.id}
                        className={`choice-tile ${isSelected ? "is-selected" : ""}`}
                      >
                        <input
                          type="radio"
                          name={`discovery-q-${currentQuestion.id}`}
                          className="visually-hidden choice-input"
                          checked={isSelected}
                          disabled={inFlight || disabled}
                          onChange={() => handleSingleSelect(opt.id)}
                        />
                        <span className="choice-indicator choice-indicator--radio" aria-hidden="true">
                          {isSelected && <span className="choice-radio-dot" />}
                        </span>
                        <span className="choice-text">{opt.label}</span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            )}

            {/* Multi Select */}
            {currentQuestion.kind === "multi_select" && (
              <fieldset className="choice-fieldset">
                <legend className="choice-group-hint">SELECT ALL THAT APPLY</legend>
                <div className="choice-list" role="group" aria-label={currentQuestion.text}>
                  {currentQuestion.options.map((opt) => {
                    const checked = selectedOptions.includes(opt.id);
                    return (
                      <label
                        key={opt.id}
                        className={`choice-tile ${checked ? "is-selected" : ""}`}
                      >
                        <input
                          type="checkbox"
                          className="visually-hidden choice-input"
                          checked={checked}
                          disabled={inFlight || disabled}
                          onChange={(e) => {
                            const isChecked = (e.target as HTMLInputElement).checked;
                            setSelectedOptions((prev) =>
                              isChecked ? [...prev, opt.id] : prev.filter((id) => id !== opt.id),
                            );
                          }}
                        />
                        <span className="choice-indicator choice-indicator--checkbox" aria-hidden="true">
                          {checked && (
                            <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                              <path d="M1 5L4.5 8.5L11 1.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          )}
                        </span>
                        <span className="choice-text">{opt.label}</span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            )}

            {/* Text Composer */}
            {currentQuestion.kind === "text" && (
              <div className="text-composer-group">
                <label className="choice-group-hint composer-label" htmlFor={`discovery-answer-${currentQuestion.id}`}>
                  YOUR ANSWER
                </label>
                <textarea
                  id={`discovery-answer-${currentQuestion.id}`}
                  ref={composerRef}
                  className="workbench-textarea composer-textarea"
                  rows={5}
                  placeholder="Describe the outcome, your contribution, or the decision behind the work…"
                  value={textAnswer}
                  onInput={(e) => handleTextChange((e.target as HTMLTextAreaElement).value)}
                  onKeyDown={handleKeyDown}
                  disabled={inFlight || disabled}
                />
                {textAnswer.trim().length > 0 && (
                  <div className="draft-status-row" aria-live="polite">
                    <span className="draft-status-indicator">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M20 6L9 17l-5-5" />
                      </svg>
                      Draft saved
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Reserved Action Dock */}
            <div className="question-actions">
              <button
                type="button"
                className="btn-primary btn-next-question"
                disabled={isSubmitDisabled}
                onClick={() => void handleSubmit()}
              >
                {submitButtonLabel}
              </button>
              {currentQuestion.allowSkip && (
                <button
                  type="button"
                  className="btn-quiet btn-skip-question"
                  disabled={inFlight || disabled}
                  onClick={() => void handleSkip()}
                >
                  Skip question
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 4. Ready for Brief Payoff Card */}
      {!isWorking && !currentQuestion && onGenerateBriefNow && (
        <div className="discovery-workbench-card ready-for-brief-card" role="status" aria-live="polite">
          <div className="workbench-top-rule" aria-hidden="true">
            <span className="workbench-sweep" />
          </div>

          <div className="workbench-header">
            <span className="eyebrow">DISCOVERY / ANSWERS COMPLETE</span>
            <span className="status-chip chip-ready">
              <span className="status-dot" aria-hidden="true" />
              Ready to synthesize
            </span>
          </div>

          <div className="ready-body">
            <h2 className="ready-headline">We have enough detail to shape your brief.</h2>
            <p className="ready-thesis">
              Discovery has analyzed your career material and your answers. Review and generate your
              structured Portfolio Discovery Brief to continue.
            </p>
            {error && <p className="start-error" role="alert">{error}</p>}
            <div className="question-actions">
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
                    setError(
                      reason instanceof Error ? reason.message : "The brief could not be started. Try again.",
                    );
                  } finally {
                    setInFlight(false);
                  }
                }}
              >
                {inFlight ? "Creating brief..." : "Create Portfolio Brief →"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
