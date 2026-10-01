import { useState } from "preact/hooks";
import type { DiscoveryViewModel } from "../../data/adapters/discovery";
import type { DiscoveryAnswerSubmission } from "../../data/discovery-answer";
import { ConversationSurface, type AnsweredTurn } from "../../components/ConversationSurface";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { AttentionPanel } from "../../components/AttentionPanel";
import { StartSurface } from "../../components/StartSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { ActionDock } from "../../components/ActionDock";
import { DiscoveryEvidenceInspector } from "../../components/DiscoveryEvidenceInspector";

export interface DiscoveryStageProps {
  view: DiscoveryViewModel | null;
  history: AnsweredTurn[];
  canMutate: boolean;
  onStartDiscovery: (notes: string) => Promise<void>;
  onSubmitAnswer: (answer: DiscoveryAnswerSubmission, isComplete: boolean) => Promise<void>;
  onContinueWithCurrentInformation: () => Promise<void>;
  onRetryDiscovery: () => Promise<void>;
  onStopDiscovery?: () => Promise<void>;
  inFlight?: boolean;
  onStartNextStage?: () => Promise<void>;
  onApproveAndContinue: () => Promise<void>;
  onReviseBrief: (revisionRequest: string) => Promise<void>;
}

export function DiscoveryStage({
  view,
  history,
  canMutate,
  onStartDiscovery,
  onSubmitAnswer,
  onContinueWithCurrentInformation,
  onRetryDiscovery,
  onStopDiscovery,
  inFlight = false,
  onApproveAndContinue,
  onStartNextStage,
  onReviseBrief,
}: DiscoveryStageProps) {

  if (!view) {
    return (
      <div className="agent-working-proof" role="status" aria-live="polite" aria-busy="true">
        <p className="eyebrow">Discovery / restoring</p>
        <h2>Opening your last confirmed proof</h2>
        <div className="working-rule" aria-hidden="true"><span /></div>
        <p>Your saved answers and brief remain on the server.</p>
      </div>
    );
  }

  if (view.state === "available") {
    return <StartSurface onStart={onStartDiscovery} disabled={!canMutate} />;
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Discovery" statusText={view.statusText} />;
  }

  // Attention / Error
  if (view.state === "attention") {
    return (
      <>
      <AttentionPanel
        title="Discovery needs attention"
        summary={view.safeError?.summary || "An issue occurred while processing your discovery answers."}
        preservedWorkNote="All your answered questions and input notes are preserved."
        retryLabel="Retry Discovery"
        onRetry={onRetryDiscovery}
        errorDetails={view.safeError ?? undefined}
      />
      {view.brief?.markdown && <section className="discovery-previous-brief" aria-label="Saved brief"><SafeMarkdown content={view.brief.markdown} /></section>}
      </>
    );
  }

  if (view.needsMoreMaterial) {
    return (
      <StartSurface
        onStart={onStartDiscovery}
        disabled={!canMutate}
        continuation
      />
    );
  }

  // Brief Review or Complete matching 03-discovery-review.png
  if (view.state === "review" || view.state === "complete") {
    return (
      <div className="discovery-brief-view">
        <DiscoveryReviewPanel
          view={view}
          canMutate={canMutate}
          inFlight={inFlight}
          onApproveAndContinue={onApproveAndContinue}
          onStartNextStage={onStartNextStage}
          onReviseBrief={onReviseBrief}
        />
      </div>
    );
  }

  // Conversation questioning mode
  const rawStatus = typeof view.raw === "object" && view.raw !== null && "status" in view.raw ? view.raw.status : "";
  const workingPhase = view.brief?.markdown ? "revision" : rawStatus === "brief_running" ? "brief" : "questions";
  return (
    <>
    <ConversationSurface
      questions={view.currentQuestions}
      history={history}
      isWorking={view.state === "working"}
      job={view.job}
      workingLabel={view.statusText}
      workingPhase={workingPhase}
      disabled={!canMutate}
      onSubmitAnswer={onSubmitAnswer}
      onContinueWithCurrentInformation={onContinueWithCurrentInformation}
      onRetryStalled={onRetryDiscovery}
      onStop={onStopDiscovery}
    />
    {view.state === "working" && view.brief?.markdown && (
      <section className="discovery-previous-brief is-revising" aria-label="Saved brief while revision runs">
        <p className="eyebrow">Previous brief · revision in progress</p>
        <SafeMarkdown content={view.brief.markdown} />
      </section>
    )}
    </>
  );
}

function DiscoveryReviewPanel({
  view,
  canMutate,
  inFlight,
  onApproveAndContinue,
  onStartNextStage,
  onReviseBrief,
}: {
  view: DiscoveryViewModel;
  canMutate: boolean;
  inFlight: boolean;
  onApproveAndContinue: () => Promise<void>;
  onStartNextStage?: () => Promise<void>;
  onReviseBrief: (revisionRequest: string) => Promise<void>;
}) {
  const [showRevisionComposer, setShowRevisionComposer] = useState(false);
  const [revisionText, setRevisionText] = useState("");
  const [revisionInFlight, setRevisionInFlight] = useState(false);

  const brief = view.brief;
  const briefTitle = brief?.title || "Discovery brief";
  const briefMarkdown = brief?.markdown || "";
  const userSummary = brief?.userSummary || "";
  const isApproved = view.state === "complete";
  const profile = brief?.profile;
  const hasProfileFacts = Boolean(
    profile &&
      (profile.name ||
        profile.currentTitle ||
        profile.location ||
        profile.skills.length ||
        profile.spokenLanguages.length),
  );

  const handleSendRevision = async () => {
    if (!revisionText.trim() || revisionInFlight) return;
    setRevisionInFlight(true);
    try {
      await onReviseBrief(revisionText.trim());
      setRevisionText("");
      setShowRevisionComposer(false);
    } finally {
      setRevisionInFlight(false);
    }
  };

  return (
    <div className="discovery-review-canvas" aria-labelledby="brief-review-heading">
      <div className="review-meta-row">
        <div className="review-status-pill">
          <span className="status-dot status-dot--sage" aria-hidden="true">●</span>
          <span>{isApproved ? "BRIEF APPROVED" : "BRIEF READY FOR REVIEW"}</span>
        </div>
      </div>

      <div className="discovery-review-layout">
        <main className="discovery-review-main">
          <header className="brief-headline-section">
            <h1 id="brief-review-heading" className="brief-title">{briefTitle}</h1>
            {userSummary && <p className="brief-subtitle">{userSummary}</p>}
          </header>

          {hasProfileFacts && profile && (
            <section className="key-details-section" aria-labelledby="discovery-profile-facts-heading">
              <h2 id="discovery-profile-facts-heading" className="key-details-header">EXTRACTED PROFILE FACTS</h2>
              <dl className="discovery-profile-facts">
                {profile.name && <div className="discovery-profile-fact"><dt className="detail-label">Name</dt><dd className="detail-value">{profile.name}</dd></div>}
                {profile.currentTitle && <div className="discovery-profile-fact"><dt className="detail-label">Current title</dt><dd className="detail-value">{profile.currentTitle}</dd></div>}
                {profile.location && <div className="discovery-profile-fact"><dt className="detail-label">Location</dt><dd className="detail-value">{profile.location}</dd></div>}
                {profile.skills.length > 0 && <div className="discovery-profile-fact"><dt className="detail-label">Skills</dt><dd className="detail-value">{profile.skills.join(", ")}</dd></div>}
                {profile.spokenLanguages.length > 0 && <div className="discovery-profile-fact"><dt className="detail-label">Languages</dt><dd className="detail-value">{profile.spokenLanguages.join(", ")}</dd></div>}
              </dl>
            </section>
          )}

          <section className="discovery-brief-document" aria-label="Complete Discovery brief">
            {briefMarkdown ? <SafeMarkdown content={briefMarkdown} /> : userSummary ? (
              <p>{userSummary}</p>
            ) : (
              <p className="discovery-inspector-empty">Brief text is unavailable in this saved state.</p>
            )}
          </section>

          {!isApproved && (
            <div className="revision-trigger-area">
              {!showRevisionComposer ? (
                <button
                  type="button"
                  className="revision-trigger-btn"
                  onClick={() => setShowRevisionComposer(true)}
                >
                  <span className="revision-icon" aria-hidden="true">✎</span>
                  <span className="revision-label">
                    <strong>Add a revision</strong> — Suggest changes or add a note before approval.
                  </span>
                </button>
              ) : (
                <div className="inline-revision-box">
                  <div className="revision-box-header">
                    <label htmlFor="discovery-revision-input">
                      <strong>Suggest changes to the brief</strong>
                    </label>
                    <p>Describe what should change in the brief or the extracted facts.</p>
                  </div>
                  <textarea
                    id="discovery-revision-input"
                    className="revision-textarea"
                    rows={4}
                    placeholder="Describe the correction or revision you want..."
                    value={revisionText}
                    onInput={(e) => setRevisionText((e.target as HTMLTextAreaElement).value)}
                    disabled={revisionInFlight}
                  />
                  <div className="revision-box-actions">
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => {
                        setShowRevisionComposer(false);
                        setRevisionText("");
                      }}
                      disabled={revisionInFlight}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="btn-primary btn-cobalt"
                      onClick={handleSendRevision}
                      disabled={revisionInFlight || !revisionText.trim()}
                    >
                      {revisionInFlight ? "Updating brief…" : "Send revision"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>

        <DiscoveryEvidenceInspector
          dossier={brief?.dossier ?? null}
          sourceDocuments={view.sourceDocuments}
          questionHistory={view.questionHistory}
        />
      </div>

      <ActionDock
        note={
          <div className="discovery-dock-step-note">
            <span className="dock-step-tag">Step 1 of 2</span>
            <span className="dock-step-name">Brief</span>
          </div>
        }
        secondaryLabel={!isApproved ? "Revise" : undefined}
        onSecondary={!isApproved ? () => setShowRevisionComposer(true) : undefined}
        primaryLabel={isApproved ? "Start Content Architect" : "Approve & continue →"}
        onPrimary={isApproved ? onStartNextStage : onApproveAndContinue}
        disabled={!canMutate || inFlight}
        busy={inFlight}
        busyLabel={isApproved ? "Starting Content Architect…" : "Approving brief…"}
      />
    </div>
  );
}
