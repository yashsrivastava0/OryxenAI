import { useEffect, useState } from "react";
import { ROUTES } from "../generated/route-registry";
import { notifyPreviewRoute } from "./PreviewBridge";

function previewBasePath(): string {
  const configured = document
    .querySelector('meta[name="oryxenai-preview-base"]')
    ?.getAttribute("content")
    ?.trim();
  if (!configured || configured === "/") return "/";
  const normalized = `/${configured.replace(/^\/+|\/+$/g, "")}/`;
  return normalized === "//" ? "/" : normalized;
}

function currentPath(): string {
  const pathname = window.location.pathname || "/";
  const base = previewBasePath();
  if (base !== "/" && pathname.startsWith(base)) {
    const route = pathname.slice(base.length - 1);
    return route || "/";
  }
  return pathname || "/";
}

export function AppRouter() {
  const [path, setPath] = useState(currentPath());
  useEffect(() => {
    const onPopState = () => setPath(currentPath());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  useEffect(() => notifyPreviewRoute(path), [path]);
  const route = ROUTES.find((candidate) => candidate.path === path);
  if (!route) {
    return <main className="route-page"><h1>Page not found</h1><p>The requested page is not part of this portfolio.</p></main>;
  }
  const Component = route.component;
  return <Component />;
}
