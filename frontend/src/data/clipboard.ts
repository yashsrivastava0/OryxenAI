export type CopyJsonResult = "copied" | "fallback" | "unavailable";

export function formatJson(value: unknown): string {
  try {
    const formatted = JSON.stringify(value, null, 2);
    return typeof formatted === "string" ? formatted : "";
  } catch {
    return "";
  }
}

function fallbackCopy(text: string): boolean {
  if (typeof document === "undefined" || typeof document.execCommand !== "function") return false;
  const field = document.createElement("textarea");
  field.value = text;
  field.readOnly = true;
  field.setAttribute("aria-hidden", "true");
  field.style.position = "fixed";
  field.style.left = "-9999px";
  field.style.top = "0";
  field.style.opacity = "0";
  document.body.appendChild(field);
  field.focus();
  field.select();
  field.setSelectionRange(0, field.value.length);
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch {
    copied = false;
  } finally {
    field.remove();
  }
  return copied;
}

export async function copyJson(text: string): Promise<CopyJsonResult> {
  if (!text) return "unavailable";
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return "copied";
    } catch {
      // Fall through to the selectable DOM fallback for local HTTP contexts,
      // permission-denied clipboard APIs, and embedded browsers.
    }
  }
  return fallbackCopy(text) ? "fallback" : "unavailable";
}
