// Deterministic test fixtures for Preview adapter testing (Phase 4).

export const previewFixtureAbsent = {
  status: "not_started",
  current_run_id: "",
  active_preview: null,
  stale: false,
};

export const previewFixtureReady = {
  status: "ready",
  current_run_id: "run_gen_1",
  active_preview: {
    origin: "https://preview.oryxenai.local",
    base_url: "https://preview.oryxenai.local/p/run_gen_1/",
    path: "/p/run_gen_1/",
    route_paths: ["/", "/about", "/projects", "/contact"],
    promoted_at: "2026-09-02T13:02:15Z",
  },
  stale: false,
};

export const previewFixtureServerReady = {
  status: "ready",
  current_run_id: "run_server_1",
  active_preview: {
    host: "preview.oryxenai.local",
    url: "https://preview.oryxenai.local/p/run_server_1/",
    candidate_id: "cand_1",
    route_paths: ["/", "/experience", "/work-samples"],
    promoted_at: "2026-09-02T14:20:00Z",
  },
  stale: false,
};

export const previewFixtureWorkingWithPrevious = {
  status: "generating",
  current_run_id: "run_gen_2",
  active_preview: {
    origin: "https://preview.oryxenai.local",
    base_url: "https://preview.oryxenai.local/p/run_gen_1/",
    path: "/p/run_gen_1/",
    route_paths: ["/", "/about"],
    promoted_at: "2026-09-02T12:00:00Z",
  },
  stale: false,
};

export const previewFixtureNeedsAttentionWithPrevious = {
  status: "needs_attention",
  current_run_id: "run_gen_3",
  latest_error: {
    message: "TypeScript compiler error during verification.",
    code: "CODE_GENERATOR_VERIFY_FAILED",
  },
  active_preview: {
    origin: "https://preview.oryxenai.local",
    base_url: "https://preview.oryxenai.local/p/run_gen_1/",
    path: "/p/run_gen_1/",
    route_paths: ["/", "/projects"],
    promoted_at: "2026-09-02T12:00:00Z",
  },
  stale: false,
};

export const previewFixtureNeedsAttentionWithoutPrevious = {
  status: "needs_attention",
  current_run_id: "run_gen_4",
  latest_error: {
    message: "Resource acquisition failed.",
    code: "RESOURCE_ACQUISITION_FAILED",
  },
  active_preview: null,
  stale: false,
};

export const previewFixtureInvalidScheme = {
  status: "ready",
  current_run_id: "run_gen_5",
  active_preview: {
    url: "javascript:alert(1)",
    route_paths: ["/"],
  },
  stale: false,
};

export const previewFixtureInvalidTraversal = {
  status: "ready",
  current_run_id: "run_gen_6",
  active_preview: {
    url: "https://preview.oryxenai.local/preview/../../secret",
    route_paths: ["/"],
  },
  stale: false,
};

export const previewFixtureStale = {
  status: "ready",
  current_run_id: "run_gen_7",
  active_preview: {
    origin: "https://preview.oryxenai.local",
    base_url: "https://preview.oryxenai.local/p/run_gen_7/",
    path: "/p/run_gen_7/",
    route_paths: ["/", "/gallery"],
  },
  stale: true,
};
