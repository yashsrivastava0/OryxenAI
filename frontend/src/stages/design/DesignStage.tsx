import { useState } from "preact/hooks";
import type { DesignViewModel, PageVisualDirectionVM } from "../../data/adapters/design";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ProgressSurface } from "../../components/ProgressSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { SceneStoryboard } from "../../components/SceneStoryboard";
import { ActionDock } from "../../components/ActionDock";

export interface DesignStageProps {
  view: DesignViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  onApproveAndContinue: () => Promise<void>;
  onStartNextStage?: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  onStop?: () => Promise<void>;
  inFlight?: boolean;
}

export function DesignStage({
  view,
  canMutate,
  onStart,
  onApproveAndContinue,
  onStartNextStage,
  onRevise,
  onStop,
  inFlight = false,
}: DesignStageProps) {

  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel" role="region" aria-label="Visual Design Director locked">
        <p className="eyebrow">Stage 03 / Visual Design Director</p>
        <h2 className="locked-title">Stage Locked</h2>
        <p className="locked-desc">
          Visual Design Director requires an approved site content plan before establishing the aesthetic systems, visual language, and page layouts.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel" role="region" aria-label="Visual Design Director available">
        <p className="eyebrow">Stage 03 / Visual Design Director</p>
        <h1 className="available-title">Ready to direct visual experience</h1>
        <p className="available-desc">
          Visual Design Director will consume your approved content plan to derive the creative thesis, the per-page visual language, and a scene-by-scene storyboard of what a visitor experiences while scrolling each page.
        </p>
        <div className="available-actions">
          <button
            type="button"
            className="btn-primary btn-cobalt"
            onClick={onStart}
            disabled={!canMutate || inFlight}
          >
            {inFlight ? "Starting Visual Design…" : "Start Visual Design Director →"}
          </button>
        </div>
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Visual Design Director" statusText={view.statusText} />;
  }

  if (view.state === "working") {
    return (
      <ProgressSurface
        stageLabel="Stage 03 / Visual Design Director"
        title="Directing the visual proof"
        currentMilestone={view.statusText || "Visual Design Director is working from the approved content plan"}
        milestones={[
          { id: "content", label: "Approved content plan received", state: "complete" },
          { id: "current", label: view.statusText || "Visual Design Director is working", state: "current" },
        ]}
        onStop={onStop}
        stopLabel="Stop Visual Design Director"
      />
    );
  }

  if (view.state === "attention") {
    return (
      <AttentionPanel
        title="Visual Design Director needs attention"
        summary={view.safeError?.summary || "Design direction synthesis encountered an issue and can be restarted."}
        preservedWorkNote="Your approved Content Plan remains safe."
        retryLabel="Retry Visual Design Director"
        onRetry={onStart}
        errorDetails={view.safeError ?? undefined}
      />
    );
  }

  // review or complete matching 05-design-storyboard.png
  return (
    <div className="design-stage-view">
      <DesignReviewPanel
        view={view}
        canMutate={canMutate}
        onApproveAndContinue={onApproveAndContinue}
        onStartNextStage={onStartNextStage}
        onRevise={onRevise}
        inFlight={inFlight}
        nextStageName="Build Preparation"
      />
    </div>
  );
}

function DesignReviewPanel({
  view,
  canMutate,
  onApproveAndContinue,
  onStartNextStage,
  onRevise,
  inFlight = false,
  nextStageName = "Build Preparation",
}: {
  view: DesignViewModel;
  canMutate: boolean;
  onApproveAndContinue: () => Promise<void>;
  onStartNextStage?: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  inFlight?: boolean;
  nextStageName?: string;
}) {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [showRevisionComposer, setShowRevisionComposer] = useState(false);
  const [revisionText, setRevisionText] = useState("");
  const [revisionInFlight, setRevisionInFlight] = useState(false);

  const isApproved = view.state === "complete";
  const lang = view.visualLanguage;
  const pages = view.pages;

  const activeRouteId = selectedRouteId || pages[0]?.routeId || "story";
  const defaultPage: PageVisualDirectionVM = {
    routeId: "story",
    title: "Story (recommended)",
    path: "/",
    purpose: "A guided narrative that balances story, work, and perspective.",
    mood: "Warm, restrained, deliberate",
    visitorTakeaway: "A trusted builder with deep technical clarity",
    firstImpression: "Quiet authority and high craft",
    storyboard: "",
    sectionRhythm: "Hero -> Proof -> Deep Dive -> Contact",
    primaryEmphasis: "Case studies",
    secondaryEmphasis: "Philosophy",
    responsiveSummary: "Single column with sticky table of contents",
    layoutIntent: "Editorial grid with generous margins",
    desktopTreatment: "Multi-column asymmetric",
    mobileTreatment: "Vertical stack",
    scenes: [],
    assetBriefIds: [],
    resourceCandidateIds: [],
  };
  const activePage: PageVisualDirectionVM = pages.find((p) => p.routeId === activeRouteId) ?? pages[0] ?? defaultPage;

  const handleSendRevision = async () => {
    if (!revisionText.trim() || revisionInFlight) return;
    setRevisionInFlight(true);
    try {
      await onRevise(revisionText.trim());
      setRevisionText("");
      setShowRevisionComposer(false);
    } finally {
      setRevisionInFlight(false);
    }
  };

  return (
    <div className="design-storyboard-canvas" aria-labelledby="design-review-heading">
      {/* Editorial Header matching 05-design-storyboard.png */}
      <div className="design-review-header">
        <p className="eyebrow">CREATIVE DIRECTION</p>
        <h1 id="design-review-heading" className="design-review-title">
          {lang.creativeThesis || "A calmer internet for serious builders."}
        </h1>
        <p className="design-review-subtitle">
          A portfolio that feels like a studio — thoughtful, rigorous, and human. We showcase depth of work,
          not noise, helping opportunities find you through clarity, craft, and context.
        </p>
      </div>

      {/* 4 Design Intent Cards Grid matching 05-design-storyboard.png */}
      <div className="design-intent-quad-grid">
        {/* Card 1: Color Behavior */}
        <div className="intent-card">
          <div className="intent-card-head">
            <span className="intent-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
            </span>
            <h3 className="intent-title">Color behavior</h3>
          </div>
          <p className="intent-body">
            {lang.colorIntent || "Warm, calm, and confident. Neutral foundation with focused accent moments to guide attention and signal action."}
          </p>
        </div>

        {/* Card 2: Typography Behavior */}
        <div className="intent-card">
          <div className="intent-card-head">
            <span className="intent-icon" aria-hidden="true">
              <span className="intent-font-symbol">Aa</span>
            </span>
            <h3 className="intent-title">Typography behavior</h3>
          </div>
          <p className="intent-body">
            {lang.typographyIntent || "Editorial serif for voice and headlines, clean sans-serif for utility. Clear hierarchy, generous rhythm, and excellent readability."}
          </p>
        </div>

        {/* Card 3: Motion */}
        <div className="intent-card">
          <div className="intent-card-head">
            <span className="intent-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </span>
            <h3 className="intent-title">Motion</h3>
          </div>
          <p className="intent-body">
            {lang.motionIntent || "Subtle, purposeful motion. Enhances meaning, respects attention, and feels tactile, not decorative."}
          </p>
        </div>

        {/* Card 4: Interaction */}
        <div className="intent-card">
          <div className="intent-card-head">
            <span className="intent-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3l7 18 3-7 7-3L3 3z" />
              </svg>
            </span>
            <h3 className="intent-title">Interaction</h3>
          </div>
          <p className="intent-body">
            Direct, intuitive, and empowering. Clear affordances, sensible defaults, and helpful feedback at every step.
          </p>
        </div>
      </div>

      {/* Route Filter Pills matching 05-design-storyboard.png */}
      <div className="route-pills-row">
        <div className="route-pills-left">
          <span className="route-pills-label">Route:</span>
          <div className="route-pills-list">
            {(pages.length > 0
              ? pages
              : [
                  { routeId: "story", title: "Story (recommended)" },
                  { routeId: "projects", title: "Projects" },
                  { routeId: "essays", title: "Essays" },
                  { routeId: "custom", title: "Custom" },
                ]
            ).map((page) => {
              const isSelected = page.routeId === activeRouteId;
              return (
                <button
                  key={page.routeId}
                  type="button"
                  className={`route-pill-btn ${isSelected ? "is-selected" : ""}`}
                  onClick={() => setSelectedRouteId(page.routeId)}
                >
                  {page.title || page.routeId}
                </button>
              );
            })}
          </div>
        </div>

        <div className="route-pills-right">
          <span className="route-pills-subtext">
            A guided narrative that balances story, work, and perspective.
          </span>
        </div>
      </div>

      {/* Scene Storyboard Section matching 05-design-storyboard.png */}
      <SceneStoryboard page={activePage} assetBriefs={view.assetBriefs} />

      {/* Revision Composer when clicked */}
      {!isApproved && showRevisionComposer && (
        <div className="inline-revision-box">
          <div className="revision-box-header">
            <label htmlFor="design-revision-input">
              <strong>Suggest adjustments to visual direction</strong>
            </label>
            <p>Request changes to color temperature, typography tone, motion scale, or scene pacing.</p>
          </div>
          <textarea
            id="design-revision-input"
            className="revision-textarea"
            rows={4}
            placeholder="e.g., Use higher contrast typography, make the hero scene more restrained..."
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
              {revisionInFlight ? "Updating visual direction…" : "Send revision"}
            </button>
          </div>
        </div>
      )}

      {/* ActionDock matching 05-design-storyboard.png */}
      <ActionDock
        note={
          <div className="design-dock-note">
            <span className="dock-chat-icon" aria-hidden="true">💬</span>
            <span className="dock-chat-text">Looks good? Approve to continue, or request changes.</span>
          </div>
        }
        secondaryLabel={!isApproved ? "Revise" : undefined}
        onSecondary={!isApproved ? () => setShowRevisionComposer(true) : undefined}
        primaryLabel={
          isApproved
            ? `Start ${nextStageName}`
            : "Approve & continue →"
        }
        onPrimary={isApproved ? onStartNextStage : onApproveAndContinue}
        disabled={!canMutate || inFlight}
        busy={inFlight}
        busyLabel={isApproved ? "Starting Build Preparation…" : "Approving direction…"}
      />
    </div>
  );
}
