import { render } from "preact";
import "./styles/shell.css";
import { AppShell } from "./app/AppShell";
import type { AuthorizedFetch, MeProjection } from "./data/api-client";

// Named exports, imported by src/oryxenai/web/static/app-auth-bootstrap.mjs
// as `const mod = await import(entryUrl)`. Keep this exact {boot, stop,
// restart} shape — it is the seam that lets bootProductShell() need zero
// changes when this replaces the legacy /static/app.js bundle. See
// docs/Frontend/06-cross-model-review-and-decisions.md §3.3.
export interface BootOptions {
  authorizedFetch: AuthorizedFetch;
  storage: Storage | null;
  me: MeProjection;
  role: string;
  developer: boolean;
  serverSessionId: string | null;
  readOnly: boolean;
}

let mountedRoot: HTMLElement | null = null;

export function boot(options: BootOptions): void {
  const root = document.getElementById("product-root");
  if (!root) return;
  mountedRoot = root;
  render(
    <AppShell
      authorizedFetch={options.authorizedFetch}
      me={options.me}
      serverSessionId={options.serverSessionId}
      readOnly={options.readOnly}
    />,
    root,
  );
}

export function stop(): void {
  if (!mountedRoot) return;
  render(null, mountedRoot);
  mountedRoot = null;
}

export function restart(options: BootOptions): void {
  stop();
  boot(options);
}
