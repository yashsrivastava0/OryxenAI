import { useState } from "preact/hooks";
import type {
  BuildPreparationViewModel,
  ComponentBriefEntryVM,
  ResourceBriefEntryVM,
  ResourceCandidateVM,
} from "../../data/adapters/preparation";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ProgressSurface } from "../../components/ProgressSurface";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { ActionDock } from "../../components/ActionDock";

export interface BuildPreparationStageProps {
  view: BuildPreparationViewModel | null;
  canMutate: boolean;
  inFlight?: boolean;
  generationInFlight?: boolean;
  onStart: () => Promise<void>;
  onRegenerate: () => Promise<void>;
  onStartGeneration?: () => Promise<void>;
}

function isHttpUrl(value: string): boolean {
  return value.startsWith("https://") || value.startsWith("http://");
}

function primaryCandidate(entry: ResourceBriefEntryVM): ResourceCandidateVM | null {
  const index = entry.primaryCandidateIndex;
  if (index !== null && entry.candidates[index]) return entry.candidates[index];
  return entry.candidates[0] ?? null;
}

function CandidateSource({ candidate }: { candidate: ResourceCandidateVM | null }) {
  if (!candidate) {
    return <span className="prep-candidate-empty">No material candidate returned</span>;
  }
  const href = candidate.previewUrl && isHttpUrl(candidate.previewUrl)
    ? candidate.previewUrl
    : candidate.url && isHttpUrl(candidate.url)
      ? candidate.url
      : "";
  return (
    <>
      <span>{candidate.provider || "Research catalogue"}</span>
      {href ? <a href={href} target="_blank" rel="noopener noreferrer">Inspect source</a> : null}
    </>
  );
}

function ResourceCard({ entry }: { entry: ResourceBriefEntryVM }) {
  const candidate = primaryCandidate(entry);
  const dimensions = candidate && candidate.width > 0 && candidate.height > 0
    ? `${candidate.width} x ${candidate.height}`
    : "Not specified";
  return (
    <article className="evidence-card">
      <div className="evidence-card-mark" aria-hidden="true">
        <span>{entry.category ? entry.category.slice(0, 1).toUpperCase() : "R"}</span>
      </div>
      <div className="evidence-card-content">
        <div className="prep-card-kicker">
          <span>{entry.category || "Resource role"}</span>
          <span>{entry.status === "candidates_found" ? "Candidate found" : "Needs fallback"}</span>
        </div>
        <h3 className="evidence-card-title">{entry.roleId}</h3>
        <p className="evidence-card-desc">
          {entry.purpose || "The generator will resolve this role from the approved visual handoff."}
        </p>
        <div className="evidence-card-meta">
          <div><span className="meta-sub">Routes</span><strong>{entry.routeIds.length || "Shared"}</strong></div>
          <div><span className="meta-sub">Candidates</span><strong>{entry.candidates.length}</strong></div>
          <div><span className="meta-sub">Dimensions</span><strong>{dimensions}</strong></div>
        </div>
        <div className="prep-card-source">
          <span className="meta-sub">Source</span>
          <CandidateSource candidate={candidate} />
        </div>
      </div>
    </article>
  );
}

function ComponentCard({ entry }: { entry: ComponentBriefEntryVM }) {
  const primaryIndex = entry.primarySuggestionIndex;
  const primary = primaryIndex !== null && entry.suggestions[primaryIndex]
    ? entry.suggestions[primaryIndex]
    : entry.suggestions[0];
  const href = primary?.itemUrl && isHttpUrl(primary.itemUrl) ? primary.itemUrl : "";
  return (
    <article className="prep-component-card">
      <div className="prep-card-kicker">
        <span>Component role</span>
        <span>{entry.suggestions.length} suggestion{entry.suggestions.length === 1 ? "" : "s"}</span>
      </div>
      <h3>{entry.roleId}</h3>
      <p>{entry.purpose || "Pattern matched from the visual build brief."}</p>
      {primary ? (
        <div className="prep-component-primary">
          <strong>{primary.title || primary.name || "Unnamed pattern"}</strong>
          <span>{primary.provider || "Research catalogue"}</span>
          {primary.description ? <small>{primary.description}</small> : null}
          {href ? <a href={href} target="_blank" rel="noopener noreferrer">Inspect pattern</a> : null}
        </div>
      ) : <span className="prep-candidate-empty">No pattern suggestion returned</span>}
    </article>
  );
}

function BriefDrawer({ eyebrow, title, markdown, filename }: {
  eyebrow: string;
  title: string;
  markdown: string;
  filename: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="collapsible-brief-card">
      <button type="button" className="collapsible-brief-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        <div className="collapsible-brief-left">
          <span className="brief-doc-icon" aria-hidden="true">▤</span>
          <div>
            <span className="brief-eyebrow">{eyebrow}</span>
            <strong className="brief-title-line">{title}</strong>
            <span className="brief-filename">{filename}</span>
          </div>
        </div>
        <span className={`brief-chevron ${open ? "is-open" : ""}`} aria-hidden="true">▾</span>
      </button>
      {open ? <div className="preparation-brief-body"><SafeMarkdown content={markdown || "No brief available."} /></div> : null}
    </div>
  );
}

export function BuildPreparationStage({
  view,
  canMutate,
  inFlight = false,
  generationInFlight = false,
  onStart,
  onRegenerate,
  onStartGeneration,
}: BuildPreparationStageProps) {
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel" role="region" aria-label="Build Preparation locked">
        <p className="eyebrow">Stage 04 / Build Preparation</p>
        <h2 className="locked-title">Stage Locked</h2>
        <p className="locked-desc">Build Preparation packages the approved Content and Visual Design handoffs into the briefs the generator will consume.</p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel" role="region" aria-label="Build Preparation available">
        <p className="eyebrow">Stage 04 / Build Preparation</p>
        <h1 className="available-title">Ready to prepare the build handoff</h1>
        <p className="available-desc">This explicit step binds both approved handoffs, compiles resource and component needs, and writes the content and visual briefs for the later generator.</p>
        <div className="available-actions">
          <button type="button" className="btn-primary btn-cobalt" onClick={() => { void onStart(); }} disabled={!canMutate || inFlight}>
            {inFlight ? "Preparing handoff..." : "Prepare build handoff →"}
          </button>
        </div>
      </div>
    );
  }

  if (view.state === "unsupported") return <UnsupportedPanel stageName="Build Preparation" statusText={view.statusText} />;

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
        summary={view.safeError?.summary || (stale ? "An approved upstream handoff changed. Regenerate the package before using it for generation." : "The build handoff could not be completed. Your approved Content and Design work remains preserved.")}
        preservedWorkNote="Approved Content and Visual Design snapshots remain unchanged."
        retryLabel={stale ? "Regenerate build handoff" : "Retry Build Preparation"}
        onRetry={stale ? onRegenerate : onStart}
        inFlight={inFlight}
        errorDetails={view.safeError ?? undefined}
        technicalDetails={view.staleReasons.length > 0 ? view.staleReasons.join("\n") : null}
      />
    );
  }

  const routeCount = view.routes.length;
  const resourceCount = view.resourceNeedsCount;
  const resourceRoleCount = view.resourceIndexCount;
  const componentCount = view.componentIndexCount;
  const generationBusy = inFlight || generationInFlight;

  return (
    <div className="preparation-stage-shell" aria-labelledby="prep-header-title">
      <div className="preparation-hero-header">
        <div className="prep-status-row">
          <span className="prep-status-badge"><span className="status-dot status-dot--sage" aria-hidden="true">●</span>READY FOR GENERATION</span>
          <span className="prep-timestamp">STABLE HANDOFF COMPILED</span>
        </div>
        <h1 id="prep-header-title" className="prep-headline">Build handoff prepared</h1>
        <p className="prep-subtitle">Two immutable briefs, bound route index, and researched resource/component candidates are compiled and hash-locked for generation.</p>
      </div>

      <div className="preparation-kpi-grid" aria-label="Build handoff facts">
        <div className="prep-kpi-card"><span className="kpi-number">{routeCount}</span><span className="kpi-label">Routes bound</span><span className="kpi-subtext">From approved route plan</span></div>
        <div className="prep-kpi-card"><span className="kpi-number">{resourceCount}</span><span className="kpi-label">Resource needs</span><span className="kpi-subtext">Requested by the brief</span></div>
        <div className="prep-kpi-card"><span className="kpi-number">{resourceRoleCount}</span><span className="kpi-label">Resource roles</span><span className="kpi-subtext">Research index entries</span></div>
        <div className="prep-kpi-card"><span className="kpi-number">{componentCount}</span><span className="kpi-label">Component roles</span><span className="kpi-subtext">Pattern index entries</span></div>
      </div>

      <section className="preparation-asset-gallery" aria-labelledby="prep-evidence-title">
        <div className="evidence-header-row">
          <div><h2 id="prep-evidence-title" className="evidence-section-title">Visual evidence &amp; resources</h2><p className="evidence-section-subtitle">Only candidates present in the Build Preparation resource index appear here.</p></div>
          <span className="evidence-count-badge">{resourceRoleCount} roles indexed</span>
        </div>
        {view.resourceIndex.length > 0 ? <div className="evidence-cards-grid">{view.resourceIndex.map((entry) => <ResourceCard key={entry.needId} entry={entry} />)}</div> : <p className="prep-empty-state">No resource roles were returned in this handoff. The generator will use approved local fallbacks where the contract permits them.</p>}
      </section>

      <section className="preparation-component-deck" aria-labelledby="prep-components-title">
        <div className="evidence-header-row">
          <div><h2 id="prep-components-title" className="evidence-section-title">Component pattern suggestions</h2><p className="evidence-section-subtitle">Pattern roles passed to the generator from the researched component index.</p></div>
          <span className="evidence-count-badge">{componentCount} roles indexed</span>
        </div>
        {view.componentIndex.length > 0 ? <div className="prep-component-grid">{view.componentIndex.map((entry) => <ComponentCard key={entry.needId} entry={entry} />)}</div> : <p className="prep-empty-state">No component suggestions were returned in this handoff.</p>}
      </section>

      <section className="preparation-routes" aria-labelledby="prep-routes-title">
        <div className="evidence-header-row">
          <div><h2 id="prep-routes-title" className="evidence-section-title">Routes bound to handoff</h2><p className="evidence-section-subtitle">Public URL structure and route plans locked for code generation.</p></div>
          <span className="evidence-count-badge">{routeCount} routes bound</span>
        </div>
        {view.routes.length > 0 ? <div className="prep-route-list">{view.routes.map((route) => <div className="prep-route-row" key={route.routeId}><code>{route.path || `/${route.routeId}`}</code><div><strong>{route.title || route.routeId}</strong><span>{route.purpose || "Approved route"}</span></div></div>)}</div> : <p className="prep-empty-state">No routes were returned in this handoff.</p>}
      </section>

      <div className="preparation-brief-grid brief-readers-section">
        <h2 className="brief-readers-header">Brief reader</h2>
        <p className="brief-readers-subtitle">The exact Markdown pair bound for the Code Generator request.</p>
        <div className="brief-cards-stack">
          <BriefDrawer eyebrow="CONTENT BRIEF" title="Content and narrative" filename="content-and-narrative-brief.md" markdown={view.contentBriefMarkdown} />
          <BriefDrawer eyebrow="VISUAL BRIEF" title="Visual and build direction" filename="visual-and-build-brief.md" markdown={view.visualBriefMarkdown} />
        </div>
      </div>

      <ActionDock
        note={<span className="prep-dock-status-phrase">Ready with {routeCount} routes, {resourceRoleCount} resource roles, and {componentCount} component roles from the approved handoff.</span>}
        secondaryLabel={canMutate ? "Regenerate handoff" : undefined}
        onSecondary={canMutate ? () => { void onRegenerate(); } : undefined}
        primaryLabel="Start generating portfolio"
        onPrimary={onStartGeneration ? () => { void onStartGeneration(); } : undefined}
        busy={generationBusy}
        busyLabel={generationInFlight ? "Starting generation..." : "Preparing handoff..."}
        disabled={!canMutate}
      />
    </div>
  );
}
