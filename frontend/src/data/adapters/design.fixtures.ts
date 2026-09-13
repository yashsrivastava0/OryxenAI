// Fixtures for Visual Design Director adapter unit tests.

export const designFixtureNotStarted = {
  status: "not_started",
};

export const designFixtureBuildRunning = {
  status: "build_running",
};

export const designFixtureReview = {
  status: "design_review",
  pages_included: true,
  user_summary: "Minimal Swiss-editorial aesthetic emphasizing technical depth, typography contrast, and structured diagrams.",
  visual_language: {
    creative_thesis: "Quiet confidence through high-density typographic hierarchy, crisp dividing rules, and purposeful motion.",
    design_keywords: ["editorial", "swiss", "minimal", "precise"],
    color_intent: "Warm paper canvas, deep obsidian ink, and a single restrained cobalt accent reserved for evidence.",
    typography_intent: "A calm display/body hierarchy; headlines read as statements, structured data uses a crisp sans.",
    motion_intent: "Subtle coordinate transitions without ambient or looping distraction.",
  },
  pages: [
    {
      route_id: "route_home",
      title: "Overview",
      path: "/",
      purpose: "Establish positioning with immediate focus on primary distributed systems impact.",
      mood: "Authoritative, calm, restrained.",
      visitor_takeaway: "This engineer designs infrastructure other engineers depend on.",
      first_impression: "A confident, text-dominant hero with a restrained diagrammatic accent.",
      storyboard: "Hero establishes positioning, then the project evidence, then a closing action.",
      section_rhythm: "hero -> about -> project -> contact",
      primary_emphasis: "the project evidence and its supporting diagram",
      secondary_emphasis: "the professional identity summary",
      layout_intent: "Editorial two-column narrative with sticky section markers.",
      desktop_treatment: "Two-column grid with 68ch measure.",
      mobile_treatment: "Single readable stream with compact collapsible sections.",
      responsive_summary: "Single column on mobile; hero centers instead of asymmetric.",
      scenes: [
        {
          scene_id: "hero_scene",
          route_id: "route_home",
          narrative_goal: "Establish positioning immediately.",
          viewport_role: "above the fold",
          content_refs: ["hero"],
          layout_intent: "Text-dominant asymmetric hero; the visual occupies one-third of the desktop composition.",
          background_intent: "A subtle structural grid texture, low contrast.",
          responsive_behavior: "Single column, centered, on mobile; asymmetric on desktop.",
          accessibility_intent: "Headline contrast exceeds WCAG AA; no motion required to read the hero.",
          acceptance_criteria: ["Headline is legible without scrolling on a standard mobile viewport."],
        },
        {
          scene_id: "project_scene",
          route_id: "route_home",
          narrative_goal: "Feature the strongest project as evidence with a diagram.",
          viewport_role: "primary evidence moment",
          content_refs: ["project"],
          layout_intent: "Framed evidence panel beside the project narrative; diagram occupies the panel.",
          asset_requirements: ["project_diagram"],
          resource_candidates: ["res_architecture_flow_01"],
          motion_intent: {
            purpose: "draw attention to the diagram as it enters view",
            trigger: "scroll into viewport",
            intensity: "subtle",
          },
          reduced_motion_behavior: "Diagram appears immediately, fully visible, with no entrance animation.",
          responsive_behavior: "Stacks vertically on mobile; diagram simplifies to a vertical flow.",
          performance_risk: "low — the diagram is a lightweight SVG, not raster media.",
          failure_safe_static_state: "The diagram is fully legible without any motion.",
          acceptance_criteria: ["The diagram communicates the retry/backoff flow without the prose."],
        },
      ],
      asset_briefs: ["project_diagram"],
      resource_candidates: ["res_architecture_flow_01"],
    },
    {
      route_id: "route_case_study_queueguard",
      title: "QueueGuard Architecture",
      path: "/case/queueguard",
      purpose: "Detailed technical walkthrough of the partition-recovery pipeline.",
      mood: "Technical, rigorous, analytical.",
      layout_intent: "Architecture diagram callouts embedded directly within structured prose.",
      desktop_treatment: "Wide code and architecture diagrams with side annotations.",
      mobile_treatment: "Stacked responsive diagrams.",
      scenes: [
        {
          scene_id: "walkthrough_scene",
          route_id: "route_case_study_queueguard",
          narrative_goal: "Walk through the partition-recovery pipeline stage by stage.",
          viewport_role: "primary content",
          layout_intent: "Annotated diagram with adjacent explanatory prose.",
          responsive_behavior: "Diagram stacks above prose on mobile.",
        },
      ],
      asset_briefs: [],
      resource_candidates: [],
    },
  ],
  asset_briefs: [
    {
      asset_id: "project_diagram",
      purpose: "Illustrate the project's retry/backoff design in place of a missing screenshot.",
      content_ref: "project:queueguard",
      asset_type: "diagram",
      source_status: "needs_acquisition",
      source_policy: "generated_local_visual",
      importance: "important",
      composition_role: "framed_evidence",
      desktop_treatment: "framed panel beside the project narrative",
      mobile_treatment: "full-width, stacked below the narrative",
      visual_treatment: "natural",
      fallback_strategy: "Fall back to a short bulleted description of the retry/backoff design.",
      decorative_vs_informative: "informative",
    },
  ],
  resource_candidates: [
    {
      resource_id: "res_architecture_flow_01",
      category: "diagram",
      why_it_matches: "Clear representation of pipeline partition recovery.",
      where_it_may_help: "route_home/project_scene",
      priority: "primary",
      possible_use: "Adapt the process-flow pattern to show the retry/backoff decision sequence.",
      adaptation_notes: "Render as clean inline SVG matching the cobalt accent.",
      confidence: "high",
    },
  ],
  conflicts: [],
  warnings: [],
};

// VISUAL_LANGUAGE_ONLY mode: creative thesis + intent, but no pages/scenes yet.
export const designFixtureLanguageOnly = {
  status: "design_review",
  pages_included: false,
  user_summary: "Foundational visual language established; page-level scene direction not yet produced.",
  visual_language: {
    creative_thesis: "Reliability engineering as its own aesthetic: restrained, high-contrast, evidence-first.",
    design_keywords: ["restrained", "high-contrast", "evidence-first"],
    color_behavior: "A single confident accent against a high-contrast neutral base.",
    typography: "A calm display/body hierarchy with generous vertical rhythm.",
    motion_character: "Minimal — reserved for one signature evidence moment.",
  },
  pages: [],
  asset_briefs: [],
  resource_candidates: [],
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
