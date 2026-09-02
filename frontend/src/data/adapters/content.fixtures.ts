// Fixtures for Content Architect adapter unit tests.

export const contentFixtureNotStarted = {
  status: "not_started",
};

export const contentFixtureBuildRunning = {
  status: "build_running",
};

export const contentFixtureReview = {
  status: "content_review",
  user_summary: "Portfolio structure designed around senior distributed-systems engineering work.",
  site_story_strategy: {
    positioning: "Staff-level infrastructure engineer leading reliability at scale.",
  },
  route_plan: [
    {
      route_id: "route_home",
      path: "/",
      title: "Overview",
      purpose: "Establish positioning and highlight primary architectural case studies.",
      publication_status: "approved",
      audience_takeaway: "Technical authority in high-throughput data systems.",
      section_sequence: ["hero", "systems_impact", "selected_work"],
    },
    {
      route_id: "route_case_study_queueguard",
      path: "/case-studies/queueguard",
      title: "QueueGuard Architecture",
      purpose: "In-depth breakdown of the zero-data-loss streaming pipeline.",
      publication_status: "approved",
      audience_takeaway: "Ability to lead multi-quarter cross-team reliability initiatives.",
      section_sequence: ["overview", "problem_statement", "architecture_decisions", "results"],
    },
  ],
  page_content_packs: [
    {
      route_id: "route_home",
      sections: [
        {
          section_id: "hero",
          purpose: "Primary introduction",
          content: {
            headline: "Designing resilient data infrastructure.",
            subheadline: "Specializing in distributed systems, consistency models, and multi-region failover.",
          },
          priority: "essential",
          optional: false,
        },
      ],
    },
  ],
  decision_basis: [
    {
      decision: "presentation_mode",
      value: "multi_page",
      basis: "source_derived",
      rationale: "Depth of project case studies warrants distinct route URLs.",
    },
  ],
  unresolved_issues: [],
  warnings: ["Omitted internal employer metrics per privacy policy."],
};

export const contentFixtureApproved = {
  ...contentFixtureReview,
  status: "approved",
};

export const contentFixtureNeedsAttention = {
  status: "needs_attention",
  latest_error: {
    message: "Generation model timed out while synthesizing page copy.",
  },
};
