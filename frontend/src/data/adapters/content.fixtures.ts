// Fixtures for Content Architect adapter unit tests.

export const contentFixtureNotStarted = {
  status: "not_started",
};

export const contentFixtureBuildRunning = {
  status: "build_running",
};

export const contentPageFixture = {
  hero: {
    name: "Priya Nandan",
    eyebrow_primary: "Senior Backend Engineer",
    eyebrow_secondary: "Reliability and data pipelines",
    headline_prefix: "Building streaming systems that",
    headline_emphasis: "never lose a message.",
    intro:
      "Priya designs durable queue and streaming infrastructure. Her recent work centers on zero-data-loss pipelines and safe migrations for high-throughput services.",
    location: "Bengaluru, India",
    primary_cta_label: "Explore the practice",
    secondary_cta_label: "View professional links",
  },
  metadata: {
    title: "Priya Nandan — Senior Backend Engineer",
    description:
      "Senior backend engineer focused on durable queues, streaming pipelines, and safe migrations for high-throughput services.",
  },
  marquee_keywords: ["Python", "Kafka", "PostgreSQL", "Kubernetes", "Go"],
  systems_practice: {
    eyebrow: "Systems practice",
    heading: "Reliable infrastructure, designed end to end.",
    intro: "The work spans queue semantics, storage, and the operations that keep them healthy.",
    pillars: [
      { title: "Durable queues", description: "At-least-once delivery with idempotent consumers." },
      { title: "Streaming pipelines", description: "Zero-data-loss ingestion at scale." },
      { title: "Safe migrations", description: "Schema and traffic moves without downtime." },
      { title: "Operations", description: "Observability and runbooks that hold up at 3 a.m." },
    ],
  },
  technical_capabilities: {
    eyebrow: "Technical capabilities",
    heading: "A backend toolkit, organized by layer.",
    intro: "Technologies named in the supplied profile.",
    groups: [
      { heading: "Languages", items: ["Python", "Go", "SQL"] },
      { heading: "Data and messaging", items: ["Kafka", "PostgreSQL", "Redis", "ClickHouse"] },
    ],
  },
  professional_context: {
    eyebrow: "Professional context",
    heading: "Experience across product engineering teams.",
    intro: "Organizations named in the supplied profile.",
    organizations: ["Example Systems", "Northwind Labs"],
  },
  connect: {
    eyebrow: "Connect",
    heading: "Explore the work.",
    intro: "Public channels for code and professional background.",
    destinations: [
      { label: "GitHub", url: "https://github.com/example", featured: true },
      { label: "LinkedIn", url: "https://linkedin.com/in/example", featured: true },
      { label: "Email", url: "mailto:priya@example.com", featured: false },
    ],
  },
};

export const contentFixtureReview = {
  status: "content_review",
  user_summary: "Page content designed around senior distributed-systems engineering work.",
  site_story_strategy: {
    positioning: "Staff-level infrastructure engineer leading reliability at scale.",
    primary_action: "Contact for a conversation",
  },
  page_content: contentPageFixture,
  claim_grounding: [
    {
      claim_id: "claim_queueguard",
      statement: "Designed the retry behavior for QueueGuard.",
      source_reference: "project/queueguard",
      source_entity_id: "project:queueguard",
      evidence_status: "verified",
      ownership: "individual",
      publication_status: "approved",
      confidence_or_warning: "",
      field_paths: ["systems_practice.pillars[0].description"],
    },
    {
      claim_id: "claim_adoption",
      statement: "Adopted by 12 teams.",
      source_reference: "",
      evidence_status: "unverified",
      ownership: "team",
      publication_status: "pending",
      confidence_or_warning: "Exact number unconfirmed.",
      field_paths: [],
    },
  ],
  coverage_ledger: [
    {
      source_id: "project/queueguard",
      disposition: "used",
      field_paths: ["systems_practice.pillars[0].title"],
      reason: "",
    },
    {
      source_id: "fact/adoption",
      disposition: "unresolved",
      field_paths: [],
      reason: "Adoption count is unconfirmed.",
    },
  ],
  internal_notes: { review: "Adoption metric omitted until confirmed." },
  decision_basis: [
    {
      decision: "primary_action",
      value: "Contact for a conversation",
      basis: "source_derived",
      rationale: "The profile targets senior backend roles.",
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
    message: "Content model timed out while synthesizing page copy.",
  },
};
