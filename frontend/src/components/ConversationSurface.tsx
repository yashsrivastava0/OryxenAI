import { useState, useEffect, useRef } from "preact/hooks";
import type { DiscoveryQuestionVM } from "../data/adapters/discovery";
import type { StageJobViewModel } from "../data/adapters/job";
import type { DiscoveryAnswerSubmission } from "../data/discovery-answer";
import { DiscoveryQuestionCard } from "./DiscoveryQuestionCard";
import { captureFailure, type FailureDiagnosticInput } from "../data/failure-diagnostics";
import { CopyDiagnosticsButton } from "./CopyDiagnosticsButton";

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
  workingPhase?: "questions" | "brief" | "revision";
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
  workingPhase = "questions",
  disabled = false,
  onSubmitAnswer,
  onContinueWithCurrentInformation,
  onRetryStalled,
  onStop,
}: ConversationSurfaceProps) {
  const [pendingIds, setPendingIds] = useState<string[]>([]);
  const saveTail = useRef<Promise<void>>(Promise.resolve());
  const saveGeneration = useRef(0);
  const visibleQuestions = questions.filter((question) => !pendingIds.includes(question.id));
  const currentQuestion = visibleQuestions[0] ?? null;
  const [inFlight, setInFlight] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [failure, setFailure] = useState<FailureDiagnosticInput | null>(null);
  const [statusAnnouncement, setStatusAnnouncement] = useState<string>("");
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!isWorking) return;
    // A revision is sent from the bottom of a long brief; bring the progress card into view.
    if (window.scrollY > 0) window.scrollTo({ top: 0, behavior: "smooth" });
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
      job?.status === "running" && heartbeatAgeSeconds !== null && heartbeatAgeSeconds >= 180,
  );
  const waitingInLine = job?.status === "queued" && queuedAgeSeconds !== null && queuedAgeSeconds >= 20;
  const phaseSteps = workingPhase === "questions"
    ? ["Source received", "Understanding background", "Preparing questions"]
    : workingPhase === "revision"
      ? ["Revision received", "Updating the brief", "Preparing your review"]
      : ["Material received", "Writing your brief", "Preparing your review"];

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return "a moment";
    if (seconds < 60) return `${Math.max(1, Math.floor(seconds))} seconds`;
    return `${Math.floor(seconds / 60)} minutes`;
  };

  useEffect(() => {
    if (questions.length > 0) {
      setStatusAnnouncement(`${questions.length} Explorer question${questions.length === 1 ? "" : "s"} ready to answer.`);
    }
  }, [questions.map((question) => question.id).join("|")]);

  useEffect(() => {
    const present = new Set(questions.map((question) => question.id));
    setPendingIds((ids) => ids.filter((id) => present.has(id)));
  }, [questions.map((question) => question.id).join("|")]);

  const handleSubmitAnswer = async (answer: DiscoveryAnswerSubmission, isComplete: boolean) => {
    if (disabled) throw new Error("Explorer is currently busy.");
    setError(null);
    setFailure(null);
    setPendingIds((ids) => [...ids, answer.questionId]);
    const generation = saveGeneration.current;
    const save = saveTail.current.then(async () => {
      if (generation !== saveGeneration.current) {
        throw new Error("An earlier answer could not be saved. Please submit it again.");
      }
      await onSubmitAnswer(answer, isComplete);
    });
    saveTail.current = save.then(() => undefined, () => undefined);
    try {
      await save;
    } catch (reason) {
      if (generation === saveGeneration.current) {
        saveGeneration.current += 1;
        setPendingIds([]);
        setError(reason instanceof Error ? reason.message : "Could not save that answer.");
        setFailure(captureFailure(reason, "discovery", "save answer", "Could not save that answer."));
      }
      throw reason;
    }
  };
  const handleStop = async () => {
    if (!onStop || stopping || disabled) return;
    setStopping(true);
    setError(null);
    setFailure(null);
    try {
      await onStop();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not stop Explorer.");
      setFailure(captureFailure(err, "discovery", "stop", "Could not stop Explorer."));
    } finally {
      setStopping(false);
    }
  };

  const handleContinueWithCurrentInformation = async () => {
    if (!onContinueWithCurrentInformation || inFlight || disabled) return;
    setInFlight(true);
    setError(null);
    setFailure(null);
    try {
      await onContinueWithCurrentInformation();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Explorer could not continue with the current information.");
      setFailure(captureFailure(reason, "discovery", "continue", "Explorer could not continue with the current information."));
    } finally {
      setInFlight(false);
    }
  };

  return (
    <section className="conversation-surface" aria-label="Explorer interview">
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
              EXPLORER / {workerStalled ? "WORKER CHECK" : workingPhase.toUpperCase()}
            </span>
            <span className="status-chip chip-active">
              <span className="status-dot pulsing" aria-hidden="true" />
              {workerStalled ? "Checking worker" : waitingInLine ? "Waiting in line" : workingPhase === "questions" ? "Reading material" : "Writing brief"}
            </span>
          </div>

          <div className="working-body">
            <h2 className="working-headline">
              {workerStalled
                ? "Explorer is waiting for the background worker"
                : waitingInLine ? "Explorer is waiting in line" : (workingLabel || "Preparing your brief.")}
            </h2>
            <p className="working-elapsed">{formatDuration(queuedAgeSeconds)} elapsed</p>

            <div className="living-draft-activity-rail" aria-hidden="true">
              <div className="activity-step step-done">
                <span className="step-point">✓</span>
                <span className="step-text">{phaseSteps[0]}</span>
              </div>
              <span className="activity-connector active" />
              <div className="activity-step step-running">
                <span className="step-point">●</span>
                <span className="step-text">{phaseSteps[1]}</span>
              </div>
              <span className="activity-connector" />
              <div className="activity-step step-pending">
                <span className="step-point">○</span>
                <span className="step-text">{phaseSteps[2]}</span>
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
                      {stopping ? "Stopping..." : "Stop Explorer"}
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="working-note">
                <p>
                  The server has your material. You may leave or refresh this page; the background job
                  persists and this workbench will update as soon as the result is ready.
                </p>
                {onStop && (
                  <div className="question-actions">
                    <button
                      type="button"
                      className="btn-quiet stop-action"
                      onClick={() => void handleStop()}
                      disabled={disabled || stopping}
                    >
                      {stopping ? "Stopping..." : "Stop Explorer"}
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

      {/* Reveal the next question while ordered saves complete in the background. */}
      {!isWorking && currentQuestion && (
        <div className="discovery-question-group" role="group" aria-label="Explorer question">
          <DiscoveryQuestionCard
            key={currentQuestion.id}
            question={currentQuestion}
            ordinal={history.length + pendingIds.length + 1}
            total={history.length + questions.length}
            isLast={visibleQuestions.length === 1}
            disabled={disabled || inFlight}
            onSubmitAnswer={handleSubmitAnswer}
          />
          {error && <p className="start-error" role="alert">{error} {failure && <CopyDiagnosticsButton failure={failure} />}</p>}
        </div>
      )}
      {!isWorking && !currentQuestion && pendingIds.length > 0 && (
        <div className="discovery-workbench-card ready-for-brief-card" role="status">
          Saving your answers and preparing the brief…
        </div>
      )}
      {/* 4. Ready for Brief Payoff Card */}
      {!isWorking && !currentQuestion && pendingIds.length === 0 && onContinueWithCurrentInformation && (
        <div className="discovery-workbench-card ready-for-brief-card" role="status" aria-live="polite">
          <div className="workbench-top-rule" aria-hidden="true">
            <span className="workbench-sweep" />
          </div>

          <div className="workbench-header">
            <span className="eyebrow">EXPLORER / READY TO CONTINUE</span>
            <span className="status-chip chip-ready">
              <span className="status-dot" aria-hidden="true" />
              Your choice
            </span>
          </div>

          <div className="ready-body">
            <h2 className="ready-headline">Continue with the information shared so far?</h2>
            <p className="ready-thesis">
              Explorer has enough context to prepare your review brief.
            </p>
            {error && <p className="start-error" role="alert">{error} {failure && <CopyDiagnosticsButton failure={failure} />}</p>}
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
