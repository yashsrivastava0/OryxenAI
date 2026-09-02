// Fixtures for Code Generator adapter unit tests.

export const generationFixtureNotStarted = {
  status: "not_started",
  current_run_id: "",
  stale: false,
};

export const generationFixtureQueued = {
  status: "queued",
  current_run_id: "run_gen_1",
  trace_id: "trace_lane_wait_123",
  started_at: "2026-09-02T13:00:00Z",
};

export const generationFixturePlanning = {
  status: "planning",
  current_run_id: "run_gen_1",
  trace_id: "trace_planning_456",
  started_at: "2026-09-02T13:00:00Z",
};

export const generationFixtureAcquiring = {
  status: "acquiring",
  current_run_id: "run_gen_1",
  trace_id: "trace_acquiring_789",
  started_at: "2026-09-02T13:00:00Z",
};

export const generationFixtureGenerating = {
  status: "generating",
  current_run_id: "run_gen_1",
  trace_id: "trace_gen_101",
  started_at: "2026-09-02T13:00:00Z",
  progress: {
    source_summary: {
      generated_routes: ["/", "/projects"],
    },
  },
};

export const generationFixtureVerifying = {
  status: "verifying",
  current_run_id: "run_gen_1",
  trace_id: "trace_verifying_202",
  started_at: "2026-09-02T13:00:00Z",
};

export const generationFixturePreviewPending = {
  status: "preview_pending",
  current_run_id: "run_gen_1",
  trace_id: "trace_pending_303",
  started_at: "2026-09-02T13:00:00Z",
};

export const generationFixtureReadyWithPreview = {
  status: "ready",
  current_run_id: "run_gen_1",
  trace_id: "trace_ready_404",
  completed_at: "2026-09-02T13:02:15Z",
  active_preview: {
    origin: "https://preview.oryxenai.local",
    base_url: "https://preview.oryxenai.local/p/run_gen_1",
    path: "/p/run_gen_1/",
    route_paths: ["/", "/projects"],
    promoted_at: "2026-09-02T13:02:15Z",
  },
  issues: [],
  stale: false,
};

export const generationFixtureReadyWithoutPreview = {
  status: "ready",
  current_run_id: "run_gen_1",
  trace_id: "trace_ready_inconsistent",
  active_preview: null,
  issues: [
    { code: "PREVIEW_PROMOTION_UNCONFIRMED", message: "Preview promotion could not be verified.", blocking: true },
  ],
  stale: false,
};

export const generationFixtureNeedsAttentionRetryable = {
  status: "needs_attention",
  current_run_id: "run_gen_1",
  trace_id: "trace_err_505",
  latest_error: {
    message: "TypeScript compiler error during verification round.",
    code: "CODE_GENERATOR_VERIFY_FAILED",
  },
  issues: [
    { code: "BUILD_LINT_ERROR", message: "Verification detected syntax/type error.", blocking: true },
  ],
  retry_status: "eligible",
  stale: false,
};

export const generationFixtureNeedsAttentionNonRetryable = {
  status: "needs_attention",
  current_run_id: "run_gen_1",
  trace_id: "trace_err_606",
  latest_error: {
    message: "Durable run aborted due to unrecoverable invariant violation.",
    code: "UNRECOVERABLE_ERROR",
  },
  retry_status: "ineligible",
  stale: false,
};

export const generationFixtureWithPreviousPreview = {
  status: "needs_attention",
  current_run_id: "run_gen_2",
  trace_id: "trace_retry_with_prev",
  latest_error: {
    message: "Second generation attempt verification failed.",
    code: "VERIFICATION_RETRY_ERROR",
  },
  active_preview: {
    origin: "https://preview.oryxenai.local",
    base_url: "https://preview.oryxenai.local/p/run_gen_1",
    path: "/p/run_gen_1/",
    route_paths: ["/", "/projects"],
    promoted_at: "2026-09-02T12:30:00Z",
  },
  retry_status: "eligible",
  stale: false,
};

export const generationFixtureUnsupported = {
  status: "quantum_synthesis_unknown",
};
