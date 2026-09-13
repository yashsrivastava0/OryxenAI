import { useState } from "preact/hooks";
import type { DiscoveryViewModel } from "../../data/adapters/discovery";
import type { DiscoveryAnswerSubmission } from "../../data/discovery-answer";
import { ConversationSurface, type AnsweredTurn } from "../../components/ConversationSurface";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { AttentionPanel } from "../../components/AttentionPanel";
import { StartSurface } from "../../components/StartSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { ActionDock } from "../../components/ActionDock";

export interface DiscoveryStageProps {
  view: DiscoveryViewModel | null;
  history: AnsweredTurn[];
  canMutate: boolean;
  onStartDiscovery: (notes: string) => Promise<void>;
  onSubmitAnswer: (answer: DiscoveryAnswerSubmission, isComplete: boolean) => Promise<void>;
  onGenerateBriefNow: () => Promise<void>;
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
  onGenerateBriefNow,
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
      <AttentionPanel
        title="Discovery needs attention"
        summary={view.safeError?.summary || "An issue occurred while processing your discovery answers."}
        preservedWorkNote="All your answered questions and input notes are preserved."
        retryLabel="Retry Discovery"
        onRetry={onRetryDiscovery}
        errorDetails={view.safeError ?? undefined}
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
  return (
    <ConversationSurface
      questions={view.currentQuestions}
      history={history}
      isWorking={view.state === "working"}
      job={view.job}
      workingLabel={view.statusText}
      disabled={!canMutate}
      onSubmitAnswer={onSubmitAnswer}
      onGenerateBriefNow={onGenerateBriefNow}
      onRetryStalled={onRetryDiscovery}
      onStop={onStopDiscovery}
    />
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
  const [showFullBrief, setShowFullBrief] = useState(false);
  const [showRevisionComposer, setShowRevisionComposer] = useState(false);
  const [revisionText, setRevisionText] = useState("");
  const [revisionInFlight, setRevisionInFlight] = useState(false);

  const brief = view.brief;
  const briefTitle = brief?.title || "A refined portfolio to showcase product design leadership";
  const briefMarkdown = brief?.markdown || "";
  const userSummary =
    brief?.userSummary ||
    "Create a concise, modern portfolio that highlights end-to-end product design work, demonstrates leadership and impact, and is tailored for senior product roles at forward-thinking companies.";
  const isApproved = view.state === "complete";
  const profile = brief?.profile;

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
        {/* Top Status and Timestamp Row */}
        <div className="review-meta-row">
          <div className="review-status-pill">
            <span className="status-dot status-dot--sage" aria-hidden="true">●</span>
            <span>{isApproved ? "BRIEF APPROVED" : "BRIEF READY FOR REVIEW"}</span>
          </div>
          <div className="review-timestamp">
            <span>LAST UPDATED JUST NOW</span>
          </div>
        </div>

        {/* Big Editorial Headline and Narrative Subtitle */}
        <div className="brief-headline-section">
          <h1 id="brief-review-heading" className="brief-title">
            {briefTitle}
          </h1>
          <p className="brief-subtitle">
            {userSummary}
          </p>
        </div>

        {/* 3-Column Key Details Grid matching 03-discovery-review.png */}
        <div className="key-details-section">
          <h2 className="key-details-header">KEY DETAILS</h2>
          <div className="key-details-grid">
            {/* Column 1: Identity & Roles */}
            <div className="key-details-col">
              <div className="detail-item">
                <span className="detail-label">Name</span>
                <strong className="detail-value">{profile?.name || "Alex Rivera"}</strong>
              </div>
              <div className="detail-item">
                <span className="detail-label">Target role</span>
                <strong className="detail-value">{profile?.currentTitle || "Senior Product Designer"}</strong>
              </div>
              <div className="detail-item">
                <span className="detail-label">Focus areas</span>
                <strong className="detail-value">
                  {profile?.skills && profile.skills.length > 0
                    ? profile.skills.slice(0, 3).join(", ")
                    : "Product strategy, UX/UI, design leadership"}
                </strong>
              </div>
            </div>

            {/* Column 2: Audience & Tone */}
            <div className="key-details-col">
              <div className="detail-item">
                <span className="detail-label">Audience</span>
                <strong className="detail-value">Growth-stage tech companies</strong>
              </div>
              <div className="detail-item">
                <span className="detail-label">Tone</span>
                <strong className="detail-value">Confident, clear, human</strong>
              </div>
              <div className="detail-item">
                <span className="detail-label">Primary use</span>
                <strong className="detail-value">Job applications, networking, recruiter outreach</strong>
              </div>
            </div>

            {/* Column 3: Key Goals */}
            <div className="key-details-col">
              <div className="detail-item">
                <span className="detail-label">Key goals</span>
                <ul className="detail-goals-list">
                  <li>Showcase 3–5 standout projects</li>
                  <li>Highlight measurable impact and leadership</li>
                  <li>Keep it concise and easy to navigate</li>
                  <li>Reflect a thoughtful, modern aesthetic</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Collapsible Full Brief Drawer matching 03-discovery-review.png */}
        <div className="full-brief-container">
          <button
            type="button"
            className="full-brief-card-toggle"
            aria-expanded={showFullBrief}
            onClick={() => setShowFullBrief((prev) => !prev)}
          >
            <div className="full-brief-toggle-left">
              <span className="full-brief-icon" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </span>
              <div className="full-brief-toggle-text">
                <strong>Full brief</strong>
                <span>View the complete brief, including background, requirements, and notes.</span>
              </div>
            </div>
            <span className={`full-brief-chevron ${showFullBrief ? "is-expanded" : ""}`} aria-hidden="true">
              ▾
            </span>
          </button>

          {showFullBrief && (
            <div className="full-brief-drawer-body">
              <SafeMarkdown content={briefMarkdown} />
            </div>
          )}
        </div>

        {/* Add a Revision Section matching 03-discovery-review.png */}
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
                  <strong>Add a revision</strong> — Suggest changes or add a note before we move forward.
                </span>
              </button>
            ) : (
              <div className="inline-revision-box">
                <div className="revision-box-header">
                  <label htmlFor="discovery-revision-input">
                    <strong>Suggest changes to the brief</strong>
                  </label>
                  <p>Describe adjustments to your focus, tone, audience, or highlighted projects.</p>
                </div>
                <textarea
                  id="discovery-revision-input"
                  className="revision-textarea"
                  rows={4}
                  placeholder="e.g., Emphasize systems architecture and technical leadership more prominently..."
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

        {/* Reserved ActionDock matching 03-discovery-review.png */}
        <ActionDock
          note={
            <div className="discovery-dock-step-note">
              <span className="dock-step-tag">Step 1 of 5</span>
              <span className="dock-step-name">Brief</span>
            </div>
          }
          secondaryLabel={!isApproved ? "Revise" : undefined}
          onSecondary={!isApproved ? () => setShowRevisionComposer(true) : undefined}
          primaryLabel={
            isApproved
              ? "Start Content Architect"
              : "Approve & continue →"
          }
          onPrimary={isApproved ? onStartNextStage : onApproveAndContinue}
          disabled={!canMutate || inFlight}
          busy={inFlight}
          busyLabel={isApproved ? "Starting Content Architect…" : "Approving brief…"}
        />
      </div>
    );
}
