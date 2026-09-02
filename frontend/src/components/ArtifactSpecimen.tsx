// Phase 1 visual/contract spike (docs/Frontend/05 §19 Phase 1): proves the
// Editorial Swiss artifact surface in code. Phase 2 replaces this with the
// real, server-driven ArtifactSurface (05 §8.5) reading approved Discovery
// briefs through the adapter.
export function ArtifactSpecimen() {
  return (
    <article className="specimen-artifact">
      <p className="eyebrow">Discover · Approved brief</p>
      <h2>A systems-minded engineer who ships</h2>
      <p>
        Five years building backend platforms, most recently leading a durable-jobs
        rewrite that cut incident response time in half. This is a static specimen
        proving the artifact surface's type, spacing, and color tokens — Phase 2
        replaces it with the real approved brief.
      </p>
    </article>
  );
}
