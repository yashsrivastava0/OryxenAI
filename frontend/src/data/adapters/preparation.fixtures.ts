export const preparationNotStarted = {
  status: "not_started",
};

export const preparationRunning = {
  status: "running",
  current_stage: "compose_visual_brief",
  elapsed_seconds: 12,
};

export const preparationReady = {
  status: "ready",
  scope_hash: "scope-123",
  routes: [{ route_id: "home", path: "/", title: "Home", purpose: "Introduce the work." }],
  resource_needs: [{ need_id: "hero", kind: "asset" }],
  resource_index: [{ need_id: "hero" }],
  component_index: [{ need_id: "cta" }],
  content_brief_markdown: "# Content brief\n\nApproved narrative.",
  visual_brief_markdown: "# Visual brief\n\nApproved direction.",
  recommended_dependencies: ["framer-motion"],
  warnings: ["Use local fallback artwork if a remote candidate is unavailable."],
  events: [{ event_id: "e1", stage: "scope", message: "Scope compiled.", timestamp: "2026-09-08T00:00:00Z" }],
  agent_output: { stage: "compose_visual_brief", nested: { retained: true } },
};

export const preparationStale = {
  ...preparationReady,
  stale: true,
  stale_reasons: ["approved_upstream_changed"],
};

export const preparationNeedsAttention = {
  status: "needs_attention",
  latest_error: { message: "The visual handoff could not be composed.", retryable: true },
};
