import type { ComponentChildren } from "preact";

export interface WorkspaceCanvasProps {
  /**
   * The persistent left activity rail. A stage composes its own journey
   * position + live activity line (via `formatActivityStatus`) into this
   * slot. This shell renders NO stage-specific content of its own — it only
   * provides the two-zone frame and responsive behavior.
   */
  rail: ComponentChildren;
  /**
   * The wider right artifact zone — the stage's actual reviewed content
   * (e.g. an ArtifactSurface). Also a generic slot.
   */
  artifact: ComponentChildren;
  /**
   * Optional short eyebrow shown as the rail's heading on wide viewports and
   * inside the compact top strip on narrow ones (e.g. "STAGE 02 / CONTENT
   * ARCHITECT"). Purely presentational; no stage logic lives here.
   */
  railLabel?: string;
  /**
   * Optional accessible label for the whole workspace region. Defaults to a
   * generic label so the shell stays stage-agnostic.
   */
  ariaLabel?: string;
  /**
   * Optional extra className appended to the root so a specific stage can
   * scope minor tweaks without this shell knowing which stage it is.
   */
  className?: string;
}

/**
 * WorkspaceCanvas — a generic, stage-agnostic "canvas split" workspace shell.
 *
 * Layout:
 *  - a persistent, narrower LEFT activity rail (`rail` slot)
 *  - a wider RIGHT artifact zone (`artifact` slot)
 *
 * Responsive: below the shared 768px workspace breakpoint the rail is
 * reprioritized into a compact top strip and the artifact zone becomes full
 * width (handled in shell.css, not by stacking every rail element). All
 * transitions consume the shared `--duration-*`/`--motion-*` tokens, which
 * already collapse to ~1ms under `prefers-reduced-motion: reduce` in
 * tokens.css — so reduced motion is honored without a duplicate override
 * here.
 *
 * This component intentionally contains NO Discovery/Content/Design/
 * Preparation/Generation markup. Each stage composes its own rail and
 * artifact content into the slots.
 */
export function WorkspaceCanvas({
  rail,
  artifact,
  railLabel,
  ariaLabel = "Stage workspace",
  className,
}: WorkspaceCanvasProps) {
  return (
    <div className={`workspace-canvas${className ? ` ${className}` : ""}`} aria-label={ariaLabel}>
      <aside className="workspace-canvas-rail" aria-label="Journey position and live activity">
        {railLabel && <p className="workspace-canvas-rail-label eyebrow">{railLabel}</p>}
        <div className="workspace-canvas-rail-body">{rail}</div>
      </aside>
      <div className="workspace-canvas-artifact" role="region" aria-label="Stage artifact">
        {artifact}
      </div>
    </div>
  );
}
