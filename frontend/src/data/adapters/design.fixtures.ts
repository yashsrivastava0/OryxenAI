// Fixtures for Visual Design Director adapter unit tests.

export const designFixtureNotStarted = {
  status: "not_started",
};

export const designFixtureBuildRunning = {
  status: "build_running",
};

export const designFixtureReview = {
  status: "design_review",
  user_summary: "Minimal Swiss-editorial aesthetic emphasizing technical depth, typography contrast, and structured diagrams.",
  visual_language: {
    creative_thesis: "Quiet confidence through high-density typographic hierarchy, crisp dividing rules, and purposeful motion.",
    design_keywords: ["editorial", "swiss", "minimal", "precise"],
    color_intent: "Warm paper canvas (#F3F0E8), deep obsidian ink (#171A19), and singular cobalt accent (#3157E7).",
    typography_intent: "Newsreader serif for architectural thesis statements; crisp system sans for structured data tables.",
    motion_intent: "Subtle coordinate transitions (120-240ms) without ambient or looping distraction.",
  },
  pages: [
    {
      route_id: "route_home",
      title: "Overview",
      purpose: "Establish positioning with immediate focus on primary distributed systems impact.",
      mood: "Authoritative, calm, restrained.",
      layout_intent: "Editorial two-column narrative with sticky section markers.",
      desktop_treatment: "Two-column grid with 68ch measure.",
      mobile_treatment: "Single readable stream with compact collapsible sections.",
    },
    {
      route_id: "route_case_study_queueguard",
      title: "QueueGuard Architecture",
      purpose: "Detailed technical walkthrough of the partition-recovery pipeline.",
      mood: "Technical, rigorous, analytical.",
      layout_intent: "Architecture diagram callouts embedded directly within structured prose.",
      desktop_treatment: "Wide code and architecture diagrams with side annotations.",
      mobile_treatment: "Stacked responsive diagrams.",
    },
  ],
  resource_candidates: [
    {
      resource_id: "res_architecture_flow_01",
      category: "diagram",
      why_it_matches: "Clear representation of pipeline partition recovery.",
      adaptation_notes: "Render as clean inline SVG matching the cobalt accent.",
    },
  ],
  conflicts: [],
  warnings: [],
};

export const designFixtureApproved = {
  ...designFixtureReview,
  status: "approved",
};

export const designFixtureNeedsAttention = {
  status: "needs_attention",
  latest_error: {
    message: "Resource catalog resolution failed for custom flow diagram.",
  },
};
