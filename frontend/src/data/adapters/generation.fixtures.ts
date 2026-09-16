export const generationNotStarted = {
  status: "not_started",
};

export const generationWorking = {
  status: "generating",
  active_job_id: "job-generate-1",
  active_job_kind: "code_generator.generate",
  progress: { coordinator_stage: "generate", current_attempt: 1, plan_summary: {}, source_summary: {} },
};

export const generationWorkingWithEstimate = {
  ...generationWorking,
  progress: {
    ...generationWorking.progress,
    stage_estimate: {
      elapsed_ms: 184000,
      estimated_total_ms: 8100000,
      estimated_remaining_ms: 7916000,
      source: "configured_budget",
    },
  },
};

export const generationReady = {
  status: "ready",
  active_preview: {
    url: "https://preview.example.test/preview/abc123/",
    route_ids: ["home"],
    route_paths: ["/"],
  },
  agent_output: { stage: "verify_and_preview", nested: { retained: true } },
};

export const generationStale = {
  ...generationReady,
  stale: true,
  stale_reasons: ["approved_upstream_changed"],
};

export const generationNeedsAttentionWithPreview = {
  status: "needs_attention",
  active_job_id: "job-verify-failed",
  active_job_kind: "code_generator.verify_and_preview",
  retry_available: true,
  active_preview: generationReady.active_preview,
  latest_error: { message: "The generated portfolio failed final verification.", retryable: true },
};

export const generationNeedsAttentionNoPreview = {
  status: "needs_attention",
  active_job_id: "job-verify-failed",
  active_job_kind: "code_generator.verify_and_preview",
  retry_available: false,
  latest_error: { message: "The generated portfolio failed final verification.", retryable: true },
};

export const generationNeedsAttentionWithCandidate = {
  ...generationNeedsAttentionNoPreview,
  candidate_preview: {
    url: "https://preview.example.test/preview/candidate/token/candidate-a/build-a/",
    route_ids: ["home"],
    route_paths: ["/", "/about"],
    verification_status: "unverified",
  },
  warnings: [{ code: "RUNTIME_REGION_GAP", message: "Optional composition spacing differs." }],
};
