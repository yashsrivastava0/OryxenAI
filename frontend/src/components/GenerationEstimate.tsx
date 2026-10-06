import { elapsedTime, generationEstimate, type GenerationKind } from "../data/generation-estimates";

export function GenerationEstimate({ kind, elapsedSeconds = null, queued = false, paused = false }: {
  kind: GenerationKind;
  elapsedSeconds?: number | null;
  queued?: boolean;
  paused?: boolean;
}) {
  const range = generationEstimate(kind);
  const elapsed = elapsedSeconds !== null && Number.isFinite(elapsedSeconds) ? Math.max(0, elapsedSeconds) : null;
  const overdue = Boolean(range && elapsed !== null && elapsed > range[1] && !queued && !paused);
  if (!range) return elapsed !== null ? <p className="progress-elapsed">{elapsedTime(elapsed)} elapsed</p> : null;
  return (
    <div className={`generation-estimate${overdue ? " is-overdue" : ""}`} aria-label="Generation time estimate">
      <div className="generation-estimate__metric">
        <span className="generation-estimate__label">Typical time</span>
        <strong>{range[0]}–{range[1]} <small>sec</small></strong>
      </div>
      {elapsed !== null && <div className="generation-estimate__metric generation-estimate__elapsed">
        <span className="generation-estimate__label">Elapsed</span>
        <strong>{elapsedTime(elapsed)}</strong>
      </div>}
      <p className="generation-estimate__note" role={overdue ? "status" : undefined}>
        {paused ? "Waiting for the worker to resume." : queued ? "Your turn starts when a worker is free." : overdue ? "Taking longer than usual. Your work is still in progress." : "An estimate, not a countdown. Detailed profiles can take longer."}
      </p>
    </div>
  );
}
