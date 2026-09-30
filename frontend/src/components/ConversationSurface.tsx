import { useState, useEffect } from "preact/hooks";
import type { DiscoveryQuestionVM } from "../data/adapters/discovery";
import type { StageJobViewModel } from "../data/adapters/job";
import type { DiscoveryAnswerSubmission } from "../data/discovery-answer";
import { DiscoveryQuestionCard } from "./DiscoveryQuestionCard";

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
  onContinueWithCurrentInformation?: () => Promise<void>;
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
  onContinueWithCurrentInformation,
  onRetryStalled,
  onStop,
}: ConversationSurfaceProps) {
  const currentQuestion = questions[0] ?? null;

  const [inFlight, setInFlight] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusAnnouncement, setStatusAnnouncement] = useState<string>("");
  const [nowMs, setNowMs] = useState(() => Date.now());

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
    if (questions.length > 0) {
      setStatusAnnouncement(`${questions.length} Discovery question${questions.length === 1 ? "" : "s"} ready to answer.`);
    }
  }, [questions.map((question) => question.id).join("|")]);

  const handleSubmitAnswer = async (answer: DiscoveryAnswerSubmission, isComplete: boolean) => {
    if (inFlight || disabled) throw new Error("Another Discovery action is still saving.");
    setInFlight(true);
    try {
      await onSubmitAnswer(answer, isComplete);
    } finally {
      setInFlight(false);
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

  const handleContinueWithCurrentInformation = async () => {
    if (!onContinueWithCurrentInformation || inFlight || disabled) return;
    setInFlight(true);
    setError(null);
    try {
      await onContinueWithCurrentInformation();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Discovery could not continue with the current information.");
    } finally {
      setInFlight(false);
    }
  };

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

      {/* Save each answer before revealing the next question. */}
      {!isWorking && currentQuestion && (
        <div className="discovery-question-group" role="group" aria-label="Discovery question">
          <DiscoveryQuestionCard
            key={currentQuestion.id}
            question={currentQuestion}
            ordinal={history.length + 1}
            total={history.length + questions.length}
            isLast={questions.length === 1}
            disabled={disabled || inFlight}
            onSubmitAnswer={handleSubmitAnswer}
          />
          {error && <p className="start-error" role="alert">{error}</p>}
        </div>
      )}
      {/* 4. Ready for Brief Payoff Card */}
      {!isWorking && !currentQuestion && onContinueWithCurrentInformation && (
        <div className="discovery-workbench-card ready-for-brief-card" role="status" aria-live="polite">
          <div className="workbench-top-rule" aria-hidden="true">
            <span className="workbench-sweep" />
          </div>

          <div className="workbench-header">
            <span className="eyebrow">DISCOVERY / READY TO CONTINUE</span>
            <span className="status-chip chip-ready">
              <span className="status-dot" aria-hidden="true" />
              Your choice
            </span>
          </div>

          <div className="ready-body">
            <h2 className="ready-headline">Continue with the information shared so far?</h2>
            <p className="ready-thesis">
              Discovery has enough context to prepare your review brief.
            </p>
            {error && <p className="start-error" role="alert">{error}</p>}
            <div className="question-actions">
              <button
                type="button"
                className="btn-primary"
                disabled={inFlight || disabled}
                onClick={() => void handleContinueWithCurrentInformation()}
              >
                {inFlight ? "Preparing review brief..." : "Continue with current information"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
