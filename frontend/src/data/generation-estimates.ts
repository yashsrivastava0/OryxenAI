export type GenerationKind = "questions" | "brief" | "content" | "studio" | "studio_edit";

/** The public shell supplies only non-secret, configured timing ranges. */
export function generationEstimate(kind: GenerationKind): [number, number] | null {
  if (typeof document === "undefined") return null;
  const content = document.querySelector('meta[name="oryxenai-generation-estimates"]')?.getAttribute("content");
  if (!content) return null;
  try {
    const range = JSON.parse(content)[kind];
    if (!Array.isArray(range) || range.length !== 2 || !range.every((n) => typeof n === "number" && Number.isFinite(n) && n > 0) || range[1] < range[0]) return null;
    return [range[0], range[1]];
  } catch {
    return null;
  }
}

export function elapsedTime(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  return whole < 60 ? `${whole}s` : `${Math.floor(whole / 60)}m ${whole % 60}s`;
}

export function elapsedSince(timestamp: string | null | undefined): number | null {
  const started = timestamp ? Date.parse(timestamp) : Number.NaN;
  return Number.isFinite(started) ? Math.max(0, (Date.now() - started) / 1000) : null;
}
