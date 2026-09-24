import { useState } from "preact/hooks";
import type { ContentViewModel } from "../../data/adapters/content";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ProgressSurface } from "../../components/ProgressSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { ActionDock } from "../../components/ActionDock";

export interface ContentStageProps {
  view: ContentViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  onApproveAndContinue: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  onStop?: () => Promise<void>;
  inFlight?: boolean;
}

export function ContentStage({
  view,
  canMutate,
  onStart,
  onApproveAndContinue,
  onRevise,
  onStop,
  inFlight = false,
}: ContentStageProps) {

  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel" role="region" aria-label="Content Architect locked">
        <p className="eyebrow">Stage 02 / Content Architect</p>
        <h2 className="locked-title">Stage Locked</h2>
        <p className="locked-desc">
          Content Architect requires an approved portfolio brief from Discovery before building your site architecture and page copy.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel" role="region" aria-label="Content Architect available">
        <p className="eyebrow">Stage 02 / Content Architect</p>
        <h1 className="available-title">Ready to structure portfolio content</h1>
        <p className="available-desc">
          Content Architect will consume your approved brief to define the site's route structure, positioning statements, and detailed section copy.
        </p>
        <div className="available-actions">
          <button
            type="button"
            className="btn-primary btn-cobalt"
            onClick={onStart}
            disabled={!canMutate || inFlight}
          >
            {inFlight ? "Starting Content Architect…" : "Start Content Architect →"}
          </button>
        </div>
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Content Architect" statusText={view.statusText} />;
  }

  if (view.state === "working") {
    return (
      <ProgressSurface
        stageLabel="Stage 02 / Content Architect"
        title="Structuring the content proof"
        currentMilestone={view.statusText || "Content Architect is working from the approved brief"}
        milestones={[
          { id: "brief", label: "Approved Discovery brief received", state: "complete" },
          { id: "current", label: view.statusText || "Content Architect is working", state: "current" },
        ]}
        onStop={onStop}
        stopLabel="Stop Content Architect"
      />
    );
  }

  if (view.state === "attention") {
    return (
      <AttentionPanel
        title="Content Architect needs attention"
        summary={view.safeError?.summary || "Content synthesis encountered an issue and can be restarted."}
        preservedWorkNote="Your approved Discovery brief remains intact."
        retryLabel="Retry Content Architect"
        onRetry={onStart}
        errorDetails={view.safeError ?? undefined}
      />
    );
  }

  // review or complete matching 04-content-route-review.png
  return (
    <div className="content-stage-view">
      <ContentReviewPanel
        view={view}
        canMutate={canMutate}
        onApproveAndContinue={onApproveAndContinue}
        onRevise={onRevise}
        inFlight={inFlight}
      />
    </div>
  );
}

function ContentReviewPanel({
  view,
  canMutate,
  onApproveAndContinue,
  onRevise,
  inFlight = false,
}: {
  view: ContentViewModel;
  canMutate: boolean;
  onApproveAndContinue: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  inFlight?: boolean;
}) {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [showRevisionComposer, setShowRevisionComposer] = useState(false);
  const [revisionText, setRevisionText] = useState("");
  const [revisionInFlight, setRevisionInFlight] = useState(false);

  const isApproved = view.state === "complete";
  const routes = view.routePlan.length > 0
    ? view.routePlan
    : [
        {
          routeId: "route_a",
          path: "/",
          title: "The Builder's Advantage",
          purpose: "A confident, evidence-led narrative that shows how you turn complexity into real-world outcomes.",
        },
        {
          routeId: "route_b",
          path: "/work",
          title: "From Insight to Impact",
          purpose: "A thought-led narrative that connects ideas to measurable change.",
        },
        {
          routeId: "route_c",
          path: "/about",
          title: "A More Human Future",
          purpose: "A people-first story about systems, creativity, and what comes next.",
        },
      ];

  const activeRouteId = selectedRouteId || routes[0]?.routeId || "route_a";
  const activeRoute = routes.find((r) => r.routeId === activeRouteId) ?? routes[0]!;

  // Resolve content packs / sections for the active route
  const activePack = view.pageContentPacks.find((p) => p.routeId === activeRoute.routeId);
  const sections = (activePack && activePack.sections.length > 0)
    ? activePack.sections
    : [
        {
          id: "sec_01",
          role: "OPENING",
          heading: "A clearer tomorrow",
          body: "Set the stage with the problem, your point of view, and why it matters now.",
        },
        {
          id: "sec_02",
          role: "APPROACH",
          heading: "Principles in practice",
          body: "Show how you work — from framing to execution — with a focus on repeatable methods.",
        },
        {
          id: "sec_03",
          role: "PROOF",
          heading: "Work that moves things",
          body: "Highlight 2–3 representative projects that demonstrate breadth and depth.",
        },
        {
          id: "sec_04",
          role: "WHAT'S NEXT",
          heading: "Bigger, together",
          body: "Close with your outlook and an invitation to collaborate.",
        },
      ];

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
    <div className="content-route-review-canvas" aria-labelledby="content-review-heading">
      {/* Header section with heading, lede, and quote callout */}
      <div className="content-review-header-row">
        <div className="content-review-titles">
          <p className="eyebrow">CONTENT REVIEW</p>
          <h1 id="content-review-heading" className="content-review-title">
            Three routes. A stronger story ahead.
          </h1>
          <p className="content-review-subtitle">
            Same foundation, three distinct angles. Review the options below, explore the full structure,
            and choose the route that best advances your portfolio goals.
          </p>
        </div>

        <div className="content-review-quote-callout" aria-hidden="true">
          <p className="quote-text">A focused narrative turns work into opportunity.</p>
          <div className="quote-divider" />
          <p className="quote-subtext">GOOD CONTENT DOES MORE THAN INFORM. IT OPENS DOORS.</p>
        </div>
      </div>

      {/* Horizontal Route Tabs Strip matching 04-content-route-review.png */}
      <div className="route-tabs-strip" role="tablist" aria-label="Portfolio content routes">
        {routes.map((route, idx) => {
          const isSelected = route.routeId === activeRouteId;
          const letter = String.fromCharCode(65 + idx); // A, B, C...
          return (
            <button
              key={route.routeId}
              type="button"
              role="tab"
              aria-selected={isSelected}
              className={`route-tab-button ${isSelected ? "is-selected" : ""}`}
              onClick={() => setSelectedRouteId(route.routeId)}
            >
              <span className="route-tab-letter">Route {letter}</span>
              <span className="route-tab-title">{route.title || `Route ${letter}`}</span>
              <span className="route-tab-arrow" aria-hidden="true">›</span>
            </button>
          );
        })}
      </div>

      {/* Selected Route Box matching 04-content-route-review.png */}
      <div className="selected-route-card" role="tabpanel" aria-labelledby={`route-tab-${activeRoute.routeId}`}>
        <div className="selected-route-header">
          <div className="selected-route-titles">
            <span className="eyebrow">SELECTED ROUTE</span>
            <h2 className="selected-route-name">{activeRoute.title || "The Builder's Advantage"}</h2>
            <p className="selected-route-desc">
              {activeRoute.purpose || "A confident, evidence-led narrative that shows how you turn complexity into real-world outcomes."}
            </p>
          </div>

          <div className="route-role-callout">
            <span className="eyebrow">ROUTE ROLE</span>
            <p className="route-role-text">
              Positions you as a pragmatic builder who connects strategy, execution, and impact.
            </p>
          </div>
        </div>

        {/* 4 Section Cards in horizontal grid */}
        <div className="route-sections-grid">
          {sections.map((rawSection, idx) => {
            const section = rawSection as Record<string, any>;
            const ordinal = String(idx + 1).padStart(2, "0");
            const heading = section.heading || section.content?.heading || section.content?.title || section.purpose || section.sectionId || `Section ${idx + 1}`;
            const body = section.body || section.content?.body || section.content?.summary || section.content?.copy || section.purpose || "";
            const role = section.role || (section.priority ? `${String(section.priority).toUpperCase()} · ${section.purpose}` : `0${idx + 1}`);
            const key = section.id || section.sectionId || idx;
            return (
              <div key={key} className="section-card">
                <div className="section-card-meta">
                  <span className="section-ordinal">{ordinal}</span>
                  <span className="section-role">{role}</span>
                </div>
                <h3 className="section-heading">{heading}</h3>
                <p className="section-body">{body}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Collapsed Alternative Routes below matching 04-content-route-review.png */}
      <div className="alternative-routes-container">
        {routes
          .filter((r) => r.routeId !== activeRouteId)
          .map((altRoute) => {
            const routeIndex = routes.findIndex((r) => r.routeId === altRoute.routeId);
            const letter = String.fromCharCode(65 + routeIndex);
            return (
              <div
                key={altRoute.routeId}
                className="collapsed-route-strip"
                onClick={() => setSelectedRouteId(altRoute.routeId)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelectedRouteId(altRoute.routeId);
                  }
                }}
              >
                <div className="collapsed-route-left">
                  <strong className="collapsed-route-letter">Route {letter}</strong>
                  <span className="collapsed-route-title">{altRoute.title}</span>
                </div>
                <div className="collapsed-route-right">
                  <span className="collapsed-route-purpose">{altRoute.purpose}</span>
                  <span className="collapsed-route-chevron" aria-hidden="true">▾</span>
                </div>
              </div>
            );
          })}
      </div>

      {/* Revision Box when requested */}
      {!isApproved && showRevisionComposer && (
        <div className="inline-revision-box">
          <div className="revision-box-header">
            <label htmlFor="content-revision-input">
              <strong>Suggest adjustments to content architecture</strong>
            </label>
            <p>Request changes to route positioning, section emphasis, or specific copy angles.</p>
          </div>
          <textarea
            id="content-revision-input"
            className="revision-textarea"
            rows={4}
            placeholder="e.g., Focus more on enterprise transformation and reduce tactical design details..."
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
              {revisionInFlight ? "Updating content…" : "Send revision"}
            </button>
          </div>
        </div>
      )}

      {isApproved && (
        <p className="approval-committed-note" role="status">
          Your content plan is approved and ready.
        </p>
      )}

      {/* ActionDock matching 04-content-route-review.png */}
      <ActionDock
        note={
          <div className="content-dock-status">
            <span className="dock-routes-count">1 route selected</span>
            <span className="dock-status-sep">|</span>
            <span className="dock-review-label">Review complete</span>
          </div>
        }
        secondaryLabel={!isApproved ? "Revise" : undefined}
        onSecondary={!isApproved ? () => setShowRevisionComposer(true) : undefined}
        primaryLabel={!isApproved ? "Approve content" : undefined}
        onPrimary={!isApproved ? onApproveAndContinue : undefined}
        disabled={!canMutate || inFlight}
        busy={inFlight}
        busyLabel="Approving content…"
      />
    </div>
  );
}
