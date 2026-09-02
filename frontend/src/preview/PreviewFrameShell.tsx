// Phase 1 static shell only — proves the frame's fixed-box sizing approach
// (docs/Frontend/02 §8 "Route and viewport controls";
// docs/Frontend/06-cross-model-review-and-decisions.md §4). No real iframe,
// receipt validation, or postMessage wiring here — that is Phase 4's
// PreviewSurface (05 §8.10).
export function PreviewFrameShell() {
  return (
    <div className="preview-frame-shell" role="img" aria-label="Preview frame specimen">
      Preview appears here after a verified build is promoted.
    </div>
  );
}
