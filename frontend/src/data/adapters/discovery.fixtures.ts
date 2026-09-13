// Fixture payloads shaped exactly like DiscoveryStateResponse.discovery
// (src/oryxenai/api/routes/discovery.py / agents/discovery/schemas.py).

export const notStarted = { status: "not_started" };

export const questionsReady = {
  status: "questions_ready",
  operation_a: {
    items: [
      {
        id: "q1",
        text: "What kind of work do you want this portfolio to lead with?",
        help_text: null,
        kind: "single_select",
        options: [
          { id: "design", label: "Design" },
          { id: "engineering", label: "Engineering" },
          { id: "writing", label: "Writing" },
        ],
        allow_skip: true,
      },
    ],
  },
  answers: { items: {} },
};

export const questionsReadyStale = {
  status: "questions_ready",
  operation_a: {
    items: [{ id: "q1", text: "Answered already", kind: "text", options: [], allow_skip: true }],
  },
  answers: { items: { q1: { question_id: "q1", mode: "answered", value: "engineering" } } },
};

const fixtureProfile = {
  name: "Jordan Rivera",
  current_title: "Senior Backend Engineer",
  location: "Remote",
  links: [{ label: "GitHub", url: "https://github.com/example" }],
  experience: [
    {
      organization: "Northwind Systems",
      role: "Senior Backend Engineer",
      dates: "2022 — Present",
      highlights: ["Led a durable-jobs rewrite that cut incident response time by half."],
    },
  ],
  education: [{ institution: "State University", credential: "B.S. Computer Science", dates: "2016 — 2020" }],
  projects: [
    {
      name: "Durable Jobs Rewrite",
      summary: "Replaced a fragile cron pipeline with a PostgreSQL-backed job queue.",
      contribution: "Sole engineer, design through rollout.",
      tech: ["Python", "PostgreSQL"],
      link: "",
    },
  ],
  skills: ["Python", "PostgreSQL", "Distributed systems", "API design"],
  spoken_languages: ["English"],
};

export const briefReview = {
  status: "brief_review",
  brief: {
    title: "A systems-minded engineer who ships",
    markdown: "# A systems-minded engineer who ships\n\nFive years building backend platforms.",
    user_summary: "Five years building backend platforms, most recently leading a durable-jobs rewrite.",
    approved: null,
    profile: fixtureProfile,
  },
};

export const approved = {
  status: "approved",
  brief: {
    title: "A systems-minded engineer who ships",
    markdown: "# A systems-minded engineer who ships\n\nFive years building backend platforms.",
    user_summary: "Five years building backend platforms, most recently leading a durable-jobs rewrite.",
    approved: { approved_at: "2026-09-02T12:00:00Z", brief_hash: "abc123" },
    profile: fixtureProfile,
  },
};

export const needsAttention = {
  status: "needs_attention",
  latest_error: { summary: "Discovery could not continue.", code: "MODEL_TIMEOUT" },
};

export const unknownFutureStatus = { status: "brief_finalizing_v2" };

export const malformed = { status: "questions_ready", operation_a: { items: "not-an-array" } };

export const questionsMcqReady = {
  status: "questions_ready",
  operation_a: {
    items: [
      {
        id: "q_mcq",
        text: "Which project stories should lead your portfolio?",
        help_text: "A focused selection helps your strongest contribution come through.",
        kind: "multi_select",
        options: [
          { id: "alphamesh", label: "AlphaMesh-Core" },
          { id: "chronos", label: "Chronos-Tick-Fabric" },
          { id: "nanosecure", label: "NanoSecure-Risk" },
        ],
        allow_skip: true,
      },
      {
        id: "q_next",
        text: "What primary audience should this portfolio address?",
        help_text: "Targeting your primary reviewer shapes language and depth.",
        kind: "text",
        options: [],
        allow_skip: true,
      },
    ],
  },
  answers: {
    items: {
      q_prior: {
        question_id: "q_prior",
        mode: "answered",
        value: "Senior Infrastructure & Reliability Engineer",
      },
    },
  },
};

export const questionsTextReady = {
  status: "questions_ready",
  operation_a: {
    items: [
      {
        id: "q_text",
        text: "What should someone understand after reading your portfolio?",
        help_text: "A sentence or two is enough. Focus on the change you helped create.",
        kind: "text",
        options: [],
        allow_skip: true,
      },
    ],
  },
  answers: {
    items: {
      q_prior_1: { question_id: "q_prior_1", mode: "answered", value: "Principal Systems Architect" },
      q_prior_2: { question_id: "q_prior_2", mode: "answered", value: "Fintech & low-latency execution" },
    },
  },
};
