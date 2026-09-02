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

export const briefReview = {
  status: "brief_review",
  brief: {
    title: "A systems-minded engineer who ships",
    user_summary: "Five years building backend platforms, most recently leading a durable-jobs rewrite.",
    approved: null,
  },
};

export const approved = {
  status: "approved",
  brief: {
    title: "A systems-minded engineer who ships",
    user_summary: "Five years building backend platforms, most recently leading a durable-jobs rewrite.",
    approved: { approved_at: "2026-09-02T12:00:00Z", brief_hash: "abc123" },
  },
};

export const needsAttention = {
  status: "needs_attention",
  latest_error: { summary: "Discovery could not continue.", code: "MODEL_TIMEOUT" },
};

export const unknownFutureStatus = { status: "brief_finalizing_v2" };

export const malformed = { status: "questions_ready", operation_a: { items: "not-an-array" } };
