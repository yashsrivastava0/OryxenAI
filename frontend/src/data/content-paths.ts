// Maps a backend page_content field path (for example
// "systems_practice.pillars[0].description") to the review card that shows it.

export const CONTENT_CARD_PREFIX = "content-card-";

export function normalizeFieldPath(path: string): string[] {
  return path
    .trim()
    .replace(/\[(\d+)\]/g, ".$1")
    .split(".")
    .filter(Boolean);
}

export function cardIdForPath(path: string, existingIds: ReadonlySet<string>): string | null {
  const segments = normalizeFieldPath(path);
  for (let length = segments.length; length > 0; length -= 1) {
    const id = `${CONTENT_CARD_PREFIX}${segments.slice(0, length).join(".")}`;
    if (existingIds.has(id)) return id;
  }
  return null;
}
