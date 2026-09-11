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
  resource_index: [
    {
      need_id: "hero",
      role_id: "home-hero-bg",
      category: "photo",
      route_ids: ["home"],
      purpose: "Hero background evoking distributed systems work.",
      status: "candidates_found",
      candidates: [
        {
          provider: "unsplash",
          url: "https://unsplash.com/photos/xyz",
          preview_url: "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800",
          title: "Server rack lights",
          license: "Unsplash License",
          attribution: "Photo by John Doe on Unsplash",
          width: 800,
          height: 533,
        },
      ],
      primary_candidate_index: 0,
    },
  ],
  component_index: [
    {
      need_id: "cta",
      role_id: "framer-motion-reveal",
      route_ids: ["home"],
      purpose: "Scroll-triggered reveal for the hero statement.",
      suggestions: [
        {
          provider: "motion/react",
          name: "motion.div",
          title: "Framer Motion reveal",
          description: "Fades and lifts an element into view on scroll.",
          item_url: "https://motion.dev/docs/react-quick-start",
        },
      ],
      primary_suggestion_index: 0,
    },
  ],
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
