import type { BuildPreparationViewModel } from "../../data/adapters/preparation";
import { AttentionPanel } from "../../components/AttentionPanel";
import { AsyncActionButton } from "../../components/AsyncActionButton";
import { ProgressSurface } from "../../components/ProgressSurface";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";

export interface BuildPreparationStageProps {
  view: BuildPreparationViewModel | null;
  canMutate: boolean;
  inFlight?: boolean;
  onStart: () => Promise<void>;
  onRegenerate: () => Promise<void>;
}

function metric(label: string, value: string | number) {
  return (
    <div className="preparation-metric" key={label}>
      <span className="metadata-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function BuildPreparationStage({
  view,
  canMutate,
  inFlight = false,
  onStart,
  onRegenerate,
}: BuildPreparationStageProps) {
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel">
        <p className="eyebrow">Stage 04 / Build Preparation</p>
        <h2>Stage Locked</h2>
        <p className="stage-desc">
          Build Preparation packages the approved Content and Visual Design handoffs into the briefs the generator will consume.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel">
        <p className="eyebrow">Stage 04 / Build Preparation</p>
        <h2>Ready to prepare the build handoff</h2>
        <p className="stage-desc">
          This explicit step binds both approved handoffs, compiles resource and component needs, and writes the content and visual briefs for the later generator.
        </p>
        <AsyncActionButton
          label="Prepare build handoff"
          busyLabel="Preparing build handoff..."
          onAction={onStart}
          disabled={!canMutate}
          inFlight={inFlight}
        />
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Build Preparation" statusText={view.statusText} />;
  }

  if (view.state === "working") {
    const current = view.currentStage || view.statusText || "Compiling the build handoff";
    return (
      <ProgressSurface
        stageLabel="Stage 04 / Build Preparation"
        title="Preparing the build proof"
        currentMilestone={current}
        elapsedSeconds={view.elapsedSeconds}
        milestones={[
          { id: "content", label: "Approved Content handoff received", state: "complete" },
          { id: "design", label: "Approved Visual Design handoff received", state: "complete" },
          { id: "current", label: current, state: "current" },
          { id: "briefs", label: "Generator briefs written", state: "quiet" },
        ]}
      />
    );
  }

  if (view.state === "attention") {
    const stale = view.stale;
    return (
      <AttentionPanel
        title={stale ? "This build handoff is out of date" : "Build Preparation needs attention"}
        summary={
          view.safeError?.summary ||
          (stale
            ? "An approved upstream handoff changed. Regenerate the package before using it for generation."
            : "The build handoff could not be completed. Your approved Content and Design work remains preserved.")
        }
        preservedWorkNote="Approved Content and Visual Design snapshots remain unchanged."
        retryLabel={stale ? "Regenerate build handoff" : "Retry Build Preparation"}
        onRetry={stale ? onRegenerate : onStart}
        inFlight={inFlight}
        errorDetails={view.safeError ?? undefined}
        technicalDetails={view.staleReasons.length > 0 ? view.staleReasons.join("\n") : null}
      />
    );
  }

  return (
    <article className="preparation-stage-view" aria-labelledby="preparation-title">
      <header className="preparation-header">
        <p className="eyebrow">BUILD PREPARATION / HANDOFF READY</p>
        <h1 id="preparation-title">Your build handoff is ready.</h1>
        <p>
          The approved narrative and visual direction are bound into a clean, generator-ready handoff. Generation and Preview remain separate later stages.
        </p>
      </header>

      <div className="preparation-metrics" aria-label="Build handoff summary">
        {metric("Routes", view.routes.length)}
        {metric("Resource needs", view.resourceNeedsCount)}
        {metric("Resource references", view.resourceIndexCount)}
        {metric("Component intents", view.componentIndexCount)}
      </div>

      {view.warnings.length > 0 && (
        <section className="preparation-notes" aria-labelledby="preparation-notes-title">
          <h2 id="preparation-notes-title">Notes for the generator</h2>
          <ul>{view.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </section>
      )}

      <div className="preparation-brief-grid">
        <section className="preparation-brief-card" aria-labelledby="content-brief-title">
          <p className="eyebrow">CONTENT BRIEF</p>
          <h2 id="content-brief-title">Content and narrative</h2>
          {view.contentBriefMarkdown ? <SafeMarkdown content={view.contentBriefMarkdown} /> : <p className="preparation-empty">The content brief is not available yet.</p>}
        </section>
        <section className="preparation-brief-card" aria-labelledby="visual-brief-title">
          <p className="eyebrow">VISUAL BRIEF</p>
          <h2 id="visual-brief-title">Visual and build direction</h2>
          {view.visualBriefMarkdown ? <SafeMarkdown content={view.visualBriefMarkdown} /> : <p className="preparation-empty">The visual brief is not available yet.</p>}
        </section>
      </div>

      {view.routes.length > 0 && (
        <section className="preparation-routes" aria-labelledby="preparation-routes-title">
          <div className="preparation-section-heading">
            <div>
              <p className="eyebrow">SCOPE INDEX</p>
              <h2 id="preparation-routes-title">Routes bound to this handoff</h2>
            </div>
            <span className="sec-badge">{view.routes.length} routes</span>
          </div>
          <ul>
            {view.routes.map((route) => (
              <li key={route.routeId}>
                <code>{route.path || route.routeId}</code>
                <span><strong>{route.title || "Untitled route"}</strong>{route.purpose ? ` ${route.purpose}` : ""}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {view.events.length > 0 && (
        <details className="preparation-events">
          <summary>Preparation events</summary>
          <ul>{view.events.map((event) => <li key={event.eventId} data-level={event.level}><span>{event.stage || "Build Preparation"}</span>{event.message}</li>)}</ul>
        </details>
      )}

      {canMutate && (
        <div className="preparation-actions">
          <button type="button" className="btn-secondary" disabled={inFlight} onClick={() => void onRegenerate()}>
            Regenerate handoff
          </button>
          <p>Regeneration is explicit and replaces this handoff only after the new durable run succeeds.</p>
        </div>
      )}
    </article>
  );
}
