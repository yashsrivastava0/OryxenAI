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

  const executeAnswer = async (fn: () => Promise<void>) => {
    if (typeof document !== "undefined" && "startViewTransition" in document) {
      (document as unknown as { startViewTransition: (cb: () => Promise<void>) => void }).startViewTransition(fn);
    } else {
      await fn();
    }
  };

  const handleTextSubmit = async () => {
    if (!currentQuestion || inFlight || disabled) return;
    const trimmed = textAnswer.trim();
    if (!trimmed) return;

    setInFlight(true);
    setError(null);
    try {
      const isLast = questions.length <= 1;
      await executeAnswer(async () => {
        await onSubmitAnswer(answeredDiscoveryQuestion(currentQuestion.id, trimmed), isLast);
        handleClearDraft();
      });
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
      await executeAnswer(async () => {
        await onSubmitAnswer(answeredDiscoveryQuestion(currentQuestion.id, optionId), isLast);
        handleClearDraft();
      });
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
      await executeAnswer(async () => {
        await onSubmitAnswer(
          answeredDiscoveryQuestion(currentQuestion.id, val ? "true" : "false"),
          isLast,
        );
        handleClearDraft();
      });
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
      await executeAnswer(async () => {
        await onSubmitAnswer(answeredDiscoveryQuestion(currentQuestion.id, selectedOptions), isLast);
        handleClearDraft();
      });
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
      await executeAnswer(async () => {
        await onSubmitAnswer(skippedDiscoveryQuestion(currentQuestion.id), isLast);
        handleClearDraft();
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not skip question.");
    } finally {
      setInFlight(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      void handleTextSubmit();
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

  const currentQuestionOrdinal = history.length + 1;
  const totalQuestionsInBatch = history.length + questions.length;
  const questionNumberLabel = `QUESTION ${String(currentQuestionOrdinal).padStart(2, "0")}${
    totalQuestionsInBatch > 0 ? ` OF ${String(totalQuestionsInBatch).padStart(2, "0")}` : ""
  }`;

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

      {/* 2. Compact Prior Answers Accordion (collapsible, keeps primary focus on active question) */}
      {!isWorking && history.length > 0 && (
        <details className="prior-answers-accordion" aria-label="Earlier answers history">
          <summary className="prior-answers-summary">
            <span className="prior-answers-count">
              <span className="summary-chevron" aria-hidden="true">▾</span>
              Earlier answers ({history.length})
            </span>
            <span className="prior-answers-hint">Click to expand previous responses</span>
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
        <div className="discovery-workbench-card active-question-card" aria-live="polite">
          <div className="workbench-top-rule" aria-hidden="true">
            <span className="workbench-sweep" />
          </div>

          <div className="workbench-header">
            <span className="eyebrow">{questionNumberLabel}</span>
            <span className="status-chip chip-ready">
              <span className="status-dot" aria-hidden="true" />
              Private draft
            </span>
          </div>

          <div className="question-content">
            <p className="question-context-tag">Based on your source material</p>
            <h2 className="question-prompt">{currentQuestion.text}</h2>
            {currentQuestion.helpText && (
              <p className="question-help">{currentQuestion.helpText}</p>
            )}

            {error && <p className="start-error" role="alert">{error}</p>}

            {/* Single Select */}
            {currentQuestion.kind === "single_select" && (
              <div className="options-grid">
                {currentQuestion.options.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    className="btn-choice"
                    disabled={inFlight || disabled}
                    onClick={() => void handleSingleSelect(opt.id)}
                  >
                    <span className="choice-indicator" aria-hidden="true">○</span>
                    <span className="choice-text">{opt.label}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Boolean */}
            {currentQuestion.kind === "boolean" && (
              <div className="options-grid boolean-grid">
                <button
                  type="button"
                  className="btn-choice"
                  disabled={inFlight || disabled}
                  onClick={() => void handleBooleanSelect(true)}
                >
                  <span className="choice-text">Yes</span>
                </button>
                <button
                  type="button"
                  className="btn-choice"
                  disabled={inFlight || disabled}
                  onClick={() => void handleBooleanSelect(false)}
                >
                  <span className="choice-text">No</span>
                </button>
              </div>
            )}

            {/* Multi Select */}
            {currentQuestion.kind === "multi_select" && (
              <div className="multi-select-form">
                <div className="checkbox-list">
                  {currentQuestion.options.map((opt) => {
                    const checked = selectedOptions.includes(opt.id);
                    return (
                      <label key={opt.id} className={`checkbox-row ${checked ? "is-selected" : ""}`}>
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
                        <span className="checkbox-label">{opt.label}</span>
                      </label>
                    );
                  })}
                </div>
                <div className="question-actions">
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={inFlight || disabled || !selectedOptions.length}
                    onClick={() => void handleMultiSelectSubmit()}
                  >
                    {inFlight ? "Saving..." : "Save answer"}
                  </button>
                  {currentQuestion.allowSkip && (
                    <button
                      type="button"
                      className="btn-quiet"
                      disabled={inFlight || disabled}
                      onClick={() => void handleSkip()}
                    >
                      Skip question
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Text Composer */}
            {currentQuestion.kind === "text" && (
              <div className="text-composer">
                <textarea
                  ref={composerRef}
                  className="workbench-textarea composer-textarea"
                  rows={4}
                  placeholder="Add the factual details or context that will make this section accurate…"
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
                    onClick={() => void handleTextSubmit()}
                  >
                    {inFlight ? "Saving..." : "Save and continue"}
                  </button>
                  {currentQuestion.allowSkip && (
                    <button
                      type="button"
                      className="btn-quiet"
                      disabled={inFlight || disabled}
                      onClick={() => void handleSkip()}
                    >
                      Skip question
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Skip action for non-text/non-multiselect */}
            {currentQuestion.kind !== "text" &&
              currentQuestion.kind !== "multi_select" &&
              currentQuestion.allowSkip && (
                <div className="question-actions secondary-actions">
                  <button
                    type="button"
                    className="btn-quiet"
                    disabled={inFlight || disabled}
                    onClick={() => void handleSkip()}
                  >
                    Skip question
                  </button>
                </div>
              )}
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
