const KEY = "oryxenai.private_return_route";
const SCREENS = new Set(["home", "guide"]);
const STAGES = new Set(["discover", "content", "studio"]);

export function privateDestination(search = "") {
  const params = new URLSearchParams(search);
  const screen = params.get("screen");
  if (screen && SCREENS.has(screen)) return `/app?screen=${screen}`;
  const stage = params.get("stage");
  if (stage && STAGES.has(stage)) return `/app?stage=${stage}`;
  return "/app";
}

export function rememberPrivateDestination(location, browser = globalThis) {
  if (location?.pathname !== "/app") return;
  try { browser?.sessionStorage?.setItem?.(KEY, privateDestination(location.search)); } catch { /* Restricted storage falls back to /app. */ }
}

export function consumePrivateDestination(browser = globalThis) {
  try {
    const storage = browser?.sessionStorage;
    const value = storage?.getItem?.(KEY);
    storage?.removeItem?.(KEY);
    if (!value) return "/app";
    const parsed = new URL(value, "https://workspace.invalid");
    return parsed.origin === "https://workspace.invalid" && parsed.pathname === "/app"
      ? privateDestination(parsed.search)
      : "/app";
  } catch { return "/app"; }
}
