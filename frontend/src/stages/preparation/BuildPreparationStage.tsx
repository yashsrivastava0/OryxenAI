import { useState } from "preact/hooks";
import type { BuildPreparationViewModel } from "../../data/adapters/preparation";
import { formatActivityStatus } from "../../data/activity-copy";
import { AttentionPanel } from "../../components/AttentionPanel";
import { AsyncActionButton } from "../../components/AsyncActionButton";
import { ProgressSurface } from "../../components/ProgressSurface";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { PeekCard } from "../../components/PeekCard";
import { WorkspaceCanvas } from "../../components/WorkspaceCanvas";

export interface BuildPreparationStageProps {
  view: BuildPreparationViewModel | null;
  canMutate: boolean;
  inFlight?: boolean;
  onStart: () => Promise<void>;
  onRegenerate: () => Promise<void>;
  onContinueToGenerate?: () => void;
}

function metric(label: string, value: string | number) {
  return (
    <div className="preparation-metric" key={label}>
      <span className="metadata-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

/**
 * The two Markdown briefs are still the authoritative generator handoff
 * (unchanged data contract), but reading them is now opt-in: they sit
 * behind an explicit "Read full brief" toggle instead of rendering by
 * default, since each can carry a large fenced JSON index block near the
 * top that used to dump straight onto the page as a wall of raw text.
 */
function BriefDrawer({ eyebrow, title, markdown }: { eyebrow: string; title: string; markdown: string }) {
  const [open, setOpen] = useState(false);
  if (!markdown) {
    return (
      <section className="preparation-brief-card">
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p className="preparation-empty">This brief is not available yet.</p>
      </section>
    );
  }
  return (
    <section className="preparation-brief-card">
      <div className="preparation-brief-card-head">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        <button type="button" className="btn-quiet" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide full brief" : "Read full brief"}
        </button>
      </div>
      {open ? (
        <div className="preparation-brief-body">
          <SafeMarkdown content={markdown} />
        </div>
      ) : (
        <p className="preparation-brief-collapsed-hint">
          {Math.round(markdown.length / 1000)}k characters — the complete generator-ready handoff, collapsed by default.
        </p>
      )}
    </section>
  );
}

export function BuildPreparationStage({
  view,
  canMutate,
  inFlight = false,
  onStart,
  onRegenerate,
  onContinueToGenerate,
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
    // Real, currently-active milestone only — no invented steps and no
    // percentage. The activity-line sweep on the "current" item is the
    // "something is genuinely happening" motion; it only ever decorates
    // the one milestone the backend actually reports as in progress.
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

  const resourceEntries = view.resourceIndex;

  // Derive the live activity line from this stage's real durable status via
  // the shared pure formatter — same precedent as ContentStage. The generic
  // WorkspaceCanvas shell holds no stage copy; it is composed here.
  const rawStatus =
    view.raw && typeof view.raw === "object" && "status" in view.raw
      ? String((view.raw as { status?: unknown }).status ?? "")
      : view.status;
  const activity = formatActivityStatus("build_preparation", rawStatus, {
    milestone: view.currentStage || null,
    stale: view.stale,
  });
  const resourcesFound = view.resourceIndex.filter((entry) => entry.status === "candidates_found").length;
  const resourcesMissing = view.resourceIndex.filter((entry) => entry.status === "no_material_found").length;

  // LEFT RAIL: journey + live activity + a compact readiness summary built
  // entirely from real adapter fields (route count, resources found vs
  // missing, component suggestion count). This is the primary at-a-glance
  // readiness signal.
  const rail = (
    <div className="content-activity-rail">
      <p className="eyebrow">Journey · Stage 04 of 05</p>
      <p className="workspace-journey-position">Build Preparation</p>
      <p
        className={`oxa-activity-line${activity.working ? " is-active" : ""}`}
        role="status"
        aria-live="polite"
      >
        {activity.text}
      </p>
      <dl className="content-activity-facts">
        <div>
          <dt>Routes bound</dt>
          <dd>{view.routes.length}</dd>
        </div>
        <div>
          <dt>Resources found</dt>
          <dd>{resourcesFound} found · {resourcesMissing} missing</dd>
        </div>
        <div>
          <dt>Component suggestions</dt>
          <dd>{view.componentIndexCount}</dd>
        </div>
      </dl>
    </div>
  );

  // RIGHT ARTIFACT ZONE: readiness signals FIRST (metrics, notes, asset
  // gallery, component deck, routes bound), then the two collapsed briefs
  // LAST — the briefs are the authoritative handoff but deliberately the
  // secondary, opt-in view.
  const artifact = (
    <article className="preparation-stage-view" aria-labelledby="preparation-title">
      <header className="preparation-header">
        <p className="eyebrow">BUILD PREPARATION / HANDOFF READY</p>
        <h1 id="preparation-title">Your build handoff is ready.</h1>
        <p>
          The approved narrative and visual direction are bound into a clean, generator-ready handoff.
        </p>
      </header>

      {onContinueToGenerate && (
        <div className="preparation-continue">
          <button type="button" className="btn-primary handoff-cta" onClick={onContinueToGenerate}>
            <span className="handoff-cta-label">Continue to Generate &amp; Preview</span>
            <svg className="handoff-cta-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      )}

      <div className="preparation-metrics" aria-label="Build handoff summary">
        {metric("Routes", view.routes.length)}
        {metric("Resource needs", view.resourceNeedsCount)}
        {metric("Discovered assets", view.resourceIndexCount)}
        {metric("Component intents", view.componentIndexCount)}
      </div>

      {view.warnings.length > 0 && (
        <section className="preparation-notes" aria-labelledby="preparation-notes-title">
          <h2 id="preparation-notes-title">Notes for the generator</h2>
          <ul>{view.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </section>
      )}

      {resourceEntries.length > 0 && (
        <section className="preparation-asset-gallery" aria-labelledby="preparation-gallery-title">
          <div className="preparation-section-heading">
            <div>
              <p className="eyebrow">RESOURCE EVIDENCE</p>
              <h2 id="preparation-gallery-title">References prepared for generation</h2>
            </div>
            <span className="sec-badge">{resourceEntries.length} intents</span>
          </div>
          <div className="resource-evidence-grid oxa-stagger">
            {resourceEntries.map((entry) => {
              const primary = entry.primaryCandidateIndex != null
                ? entry.candidates[entry.primaryCandidateIndex]
                : entry.candidates[0];
              const sourceUrl = primary?.url && /^https?:\/\//i.test(primary.url) ? primary.url : null;
              return (
                <article key={entry.needId} className="resource-evidence-card">
                  <div className="resource-evidence-intent" aria-hidden="true">
                    {entry.roleId.slice(0, 1).toUpperCase() || "R"}
                  </div>
                  <div className="resource-evidence-copy">
                    <p className="metadata-label">{entry.roleId}</p>
                    <h3>{primary?.title || entry.category || "Resource intent"}</h3>
                    <p>{entry.purpose || "A bounded resource intent is ready for the generator."}</p>
                    <dl className="resource-evidence-meta">
                      <div><dt>Status</dt><dd>{entry.status === "candidates_found" ? "Candidate found" : "Safe fallback"}</dd></div>
                      {primary?.provider && <div><dt>Provider</dt><dd>{primary.provider}</dd></div>}
                      {primary?.license && <div><dt>License</dt><dd>{primary.license}</dd></div>}
                      {primary && primary.width > 0 && primary.height > 0 && <div><dt>Dimensions</dt><dd>{primary.width} x {primary.height}</dd></div>}
                    </dl>
                    {entry.routeIds.length > 0 && <p className="resource-evidence-bound">Bound to {entry.routeIds.join(", ")}</p>}
                    {sourceUrl && <a href={sourceUrl} target="_blank" rel="noopener noreferrer">View source</a>}
                  </div>
              </article>
            );
            })}
          </div>
        </section>
      )}

      {resourceEntries.some((entry) => entry.status === "no_material_found") && (
        <details className="preparation-events">
          <summary>Resource fallback notes</summary>
          <ul className="preparation-resource-list">
            {resourceEntries.filter((entry) => entry.status === "no_material_found").map((entry) => (
              <li key={entry.needId}>
                <strong>{entry.roleId}</strong> <span className="preparation-resource-category">({entry.category || "resource"})</span>
                <p>{entry.purpose}</p>
                {entry.status === "no_material_found" && <span className="preparation-resource-none">No material found — the generator will use a safe fallback.</span>}
              </li>
            ))}
          </ul>
        </details>
      )}

      {view.componentIndex.length > 0 && (
        <section className="preparation-component-deck" aria-labelledby="preparation-components-title">
          <div className="preparation-section-heading">
            <div>
              <p className="eyebrow">RESEARCHED COMPONENTS</p>
              <h2 id="preparation-components-title">Component pattern suggestions</h2>
            </div>
            <span className="sec-badge">{view.componentIndex.length} roles</span>
          </div>
          {view.componentIndex.map((entry) => {
            const primary = entry.primarySuggestionIndex != null ? entry.suggestions[entry.primarySuggestionIndex] : entry.suggestions[0];
            return (
              <PeekCard
                key={entry.needId}
                eyebrow={entry.roleId}
                title={primary?.title || primary?.name || entry.roleId}
                badge={entry.routeIds[0]}
                summary={entry.purpose}
              >
                <ul className="preparation-component-suggestions">
                  {entry.suggestions.map((s, idx) => (
                    <li key={idx}>
                      <strong>{s.title || s.name}</strong> <span className="preparation-resource-category">({s.provider})</span>
                      {s.description && <p>{s.description}</p>}
                      {s.itemUrl && (
                        <a href={s.itemUrl} target="_blank" rel="noopener noreferrer">Documentation ↗</a>
                      )}
                    </li>
                  ))}
                </ul>
              </PeekCard>
            );
          })}
        </section>
      )}

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

      {/* SECONDARY: the two full Markdown briefs, collapsed by default via
          BriefDrawer, moved to the very end so readiness signals lead. */}
      <div className="preparation-brief-grid">
        <BriefDrawer eyebrow="CONTENT BRIEF" title="Content and narrative" markdown={view.contentBriefMarkdown} />
        <BriefDrawer eyebrow="VISUAL BRIEF" title="Visual and build direction" markdown={view.visualBriefMarkdown} />
      </div>
    </article>
  );

  return (
    <div className="preparation-stage-shell">
      <WorkspaceCanvas
        railLabel="Stage 04 / Build Preparation"
        ariaLabel="Build Preparation workspace"
        rail={rail}
        artifact={artifact}
      />
    </div>
  );
}
