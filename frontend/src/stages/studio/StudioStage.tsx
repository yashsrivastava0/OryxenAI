import { useCallback, useState } from "preact/hooks";
import type { StudioPreviewGrant } from "../../data/api-client";
import { studioMilestones, type StudioViewModel } from "../../data/adapters/studio";
import { ProgressSurface } from "../../components/ProgressSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { ChatPane } from "../../components/studio/ChatPane";
import { FailurePanel } from "../../components/studio/FailurePanel";
import { PreviewPane } from "../../components/studio/PreviewPane";
import type { FailureDiagnosticInput } from "../../data/failure-diagnostics";
import { CopyDiagnosticsButton } from "../../components/CopyDiagnosticsButton";

export interface StudioStageProps {
  view: StudioViewModel | null;
  contentApproved: boolean;
  /** Another stage mutation is in progress; hold new studio requests. */
  canMutate: boolean;
  /** A studio request (start, stop, send, restore) is in progress. */
  inFlight: boolean;
  /** Why the automatic start after approval did not begin, if it did not. */
  startError?: string | null;
  startFailure?: FailureDiagnosticInput | null;
  loadPreview: (versionId: string) => Promise<StudioPreviewGrant>;
  onStart: () => Promise<void>;
  onStop: () => Promise<void>;
  onSend: (message: string, clientMessageId: string) => Promise<void>;
  onRestore: (versionId: string) => Promise<void>;
  onBackToContent?: () => void;
}

export function StudioStage({
  view,
  contentApproved,
  canMutate,
  inFlight,
  startError = null,
  startFailure = null,
  loadPreview,
  onStart,
  onStop,
  onSend,
  onRestore,
  onBackToContent,
}: StudioStageProps) {
  const [tab, setTab] = useState<"chat" | "preview">("preview");
  const stableLoadPreview = useCallback((versionId: string) => loadPreview(versionId), [loadPreview]);

  if (!contentApproved || !view || view.state === "locked") {
    return (
      <div className="stage-locked-panel" role="region" aria-label="Studio locked">
        <p className="eyebrow">Stage 03 / Studio</p>
        <h2 className="locked-title">Stage Locked</h2>
        <p className="locked-desc">
          Approve your content plan first. The Studio builds your portfolio page from exactly that approved copy.
        </p>
        {onBackToContent ? (
          <button type="button" className="btn-secondary" onClick={onBackToContent}>
            Go to the content plan
          </button>
        ) : null}
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Studio" statusText={view.statusText} />;
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel studio-available" role="region" aria-label="Studio available">
        <p className="eyebrow">Stage 03 / Studio</p>
        <h1 className="available-title">Your content is approved. Let’s build the page.</h1>
        <p className="available-desc">
          The Studio writes your one-page portfolio from exactly the copy you approved, checks every word and link, then shows it live next to a chat where you can ask for changes.
        </p>
        {startError ? <p className="studio-inline-error" role="alert">{startError} {startFailure && <CopyDiagnosticsButton failure={startFailure} />}</p> : null}
        <div className="available-actions">
          <button
            type="button"
            className="btn-primary btn-cobalt"
            onClick={() => void onStart()}
            disabled={!canMutate || inFlight}
          >
            {inFlight ? "Starting…" : "Generate my portfolio →"}
          </button>
        </div>
      </div>
    );
  }

  if (view.state === "working" && view.inFlight) {
    const stage = view.inFlight.stage;
    return (
      <ProgressSurface
        stageLabel="Stage 03 / Studio"
        title="Building your portfolio"
        currentMilestone={
          stage === "queued" ? "Waiting for a free builder — your page starts as soon as one is available" : "Writing and checking your page"
        }
        milestones={studioMilestones(stage)}
        elapsedSeconds={view.inFlight.elapsedSeconds}
        onStop={onStop}
        stopLabel="Stop building"
      />
    );
  }

  if (view.state === "attention") {
    return (
      <div className="studio-attention">
        {view.lastError ? (
          <FailurePanel
            failure={view.lastError}
            occurredAt={view.versions.find((version) => version.failure?.reference === view.lastError?.reference)?.completedAt ?? view.job?.finishedAt}
            title={
              view.lastError.code === "JOB_CANCELLED"
                ? "The build was stopped"
                : "Your portfolio could not be built yet"
            }
            preservedNote="Your approved content is safe and unchanged. Nothing was published."
            retryLabel="Try building again"
            onRetry={onStart}
            inFlight={inFlight}
          />
        ) : (
          <div className="studio-failure" role="alert">
            <h3>Your portfolio could not be built yet</h3>
            <p>The builder stopped without a report. Your approved content is safe.</p>
            <CopyDiagnosticsButton failure={{ stage: "studio", action: "build", summary: "The builder stopped without a report.", code: "BUILD_REPORT_MISSING", jobId: view.job?.id, occurredAt: view.job?.finishedAt }} />
            <button type="button" className="btn-primary" onClick={() => void onStart()} disabled={inFlight}>
              Try building again
            </button>
          </div>
        )}
      </div>
    );
  }

  // Workspace: chat on the left, the live preview on the right.
  return (
    <div className="studio-workspace" data-tab={tab}>
      <div className="studio-tabs" role="tablist" aria-label="Studio panels">
        <button type="button" role="tab" aria-selected={tab === "chat"} onClick={() => setTab("chat")}>
          Chat
        </button>
        <button type="button" role="tab" aria-selected={tab === "preview"} onClick={() => setTab("preview")}>
          Preview
        </button>
      </div>
      <div className="studio-pane studio-pane--chat">
        <ChatPane
          chat={view.chat}
          versions={view.versions}
          activeVersionId={view.activeVersionId}
          inFlight={view.inFlight}
          lastError={view.lastError}
          busy={inFlight || !canMutate}
          onSend={onSend}
          onStop={onStop}
          onRestore={onRestore}
        />
      </div>
      <div className="studio-pane studio-pane--preview">
        <PreviewPane
          versionId={view.activeVersionId}
          versionNumber={view.activeVersionNumber}
          loadPreview={stableLoadPreview}
          updating={view.building}
        />
      </div>
    </div>
  );
}
