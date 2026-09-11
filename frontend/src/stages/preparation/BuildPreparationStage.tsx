import { useState } from "preact/hooks";
import type { BuildPreparationViewModel } from "../../data/adapters/preparation";
import { AttentionPanel } from "../../components/AttentionPanel";
import { AsyncActionButton } from "../../components/AsyncActionButton";
import { ProgressSurface } from "../../components/ProgressSurface";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { PeekCard } from "../../components/PeekCard";

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

  const IMAGE_CATEGORIES = new Set(["image", "photo", "editorial_photo", "portrait"]);
  const imageEntries = view.resourceIndex.filter((entry) => IMAGE_CATEGORIES.has(entry.category.toLowerCase()));
  const otherResourceEntries = view.resourceIndex.filter((entry) => !imageEntries.includes(entry));
  const galleryTiles = imageEntries.flatMap((entry) =>
    entry.candidates
      .filter((c) => c.previewUrl)
      .map((candidate) => ({ entry, candidate })),
  );

  return (
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

      {galleryTiles.length > 0 && (
        <section className="preparation-asset-gallery" aria-labelledby="preparation-gallery-title">
          <div className="preparation-section-heading">
            <div>
              <p className="eyebrow">RESEARCHED IMAGERY</p>
              <h2 id="preparation-gallery-title">Discovered photography</h2>
            </div>
            <span className="sec-badge">{galleryTiles.length} candidates</span>
          </div>
          <div className="asset-gallery-grid oxa-stagger">
            {galleryTiles.map(({ entry, candidate }, idx) => (
              <figure key={`${entry.needId}-${idx}`} className="asset-gallery-tile">
                <img
                  src={candidate.previewUrl}
                  alt={candidate.title || entry.purpose || "Discovered candidate image"}
                  loading="lazy"
                  width={candidate.width || undefined}
                  height={candidate.height || undefined}
                />
                <figcaption>
                  <span className="asset-gallery-title">{candidate.title || entry.roleId}</span>
                  <span className="asset-gallery-meta">{candidate.provider}{candidate.license ? ` · ${candidate.license}` : ""}</span>
                  {entry.routeIds.length > 0 && (
                    <span className="asset-gallery-bound">Bound: {entry.routeIds.join(", ")}</span>
                  )}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      {otherResourceEntries.length > 0 && (
        <details className="preparation-events">
          <summary>Other researched resources · {otherResourceEntries.length}</summary>
          <ul className="preparation-resource-list">
            {otherResourceEntries.map((entry) => (
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

      <div className="preparation-brief-grid">
        <BriefDrawer eyebrow="CONTENT BRIEF" title="Content and narrative" markdown={view.contentBriefMarkdown} />
        <BriefDrawer eyebrow="VISUAL BRIEF" title="Visual and build direction" markdown={view.visualBriefMarkdown} />
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
