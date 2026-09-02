// Fixtures for Build Preparation adapter unit tests.

export const preparationFixtureNotStarted = {
  status: "not_started",
  current_stage: "not_started",
  routes: [],
  warnings: [],
};

export const preparationFixtureRunningStage0 = {
  status: "running",
  current_stage: "stage_0",
  routes: [
    { route_id: "route_home", path: "/", title: "Overview" },
  ],
  warnings: [],
  started_at: "2026-09-02T12:00:00Z",
  elapsed_seconds: 4.2,
};

export const preparationFixtureRunningStage2 = {
  status: "running",
  current_stage: "stage_2",
  routes: [
    { route_id: "route_home", path: "/", title: "Overview" },
    { route_id: "route_about", path: "/about", title: "About" },
  ],
  warnings: [],
  started_at: "2026-09-02T12:00:00Z",
  elapsed_seconds: 12.5,
};

export const preparationFixtureRunningStage4 = {
  status: "running",
  current_stage: "stage_4",
  routes: [
    { route_id: "route_home", path: "/", title: "Overview" },
    { route_id: "route_about", path: "/about", title: "About" },
  ],
  warnings: [],
  started_at: "2026-09-02T12:00:00Z",
  elapsed_seconds: 22.1,
};

export const preparationFixtureRunningMaterialize = {
  status: "running",
  current_stage: "materialize",
  routes: [
    { route_id: "route_home", path: "/", title: "Overview" },
    { route_id: "route_about", path: "/about", title: "About" },
  ],
  warnings: ["Omitted external font fetch; fallback used."],
  started_at: "2026-09-02T12:00:00Z",
  elapsed_seconds: 35.8,
};

export const preparationFixtureRunningUnknown = {
  status: "running",
  current_stage: "some_new_internal_substage_xyz",
  routes: [
    { route_id: "route_home", path: "/", title: "Overview" },
  ],
  warnings: [],
  started_at: "2026-09-02T12:00:00Z",
  elapsed_seconds: 18.0,
};

export const preparationFixtureReadyEligible = {
  status: "ready",
  current_stage: "ready",
  routes: [
    { route_id: "route_home", path: "/", title: "Overview" },
    { route_id: "route_projects", path: "/projects", title: "Projects" },
  ],
  handoff_report: {
    handoff_eligible: true,
    status: "ready_for_handoff",
    upstream_approval_verified: true,
    issues: [],
  },
  package: {
    pack_version: "build-preparation-pack-v3",
    archive_sha256: "abc123sha",
    file_count: 24,
    expires_at: "2026-09-10T12:00:00Z",
    artifact: {
      provider: "r2",
      key: "build-packs/abc123sha.zip",
      sha256: "abc123sha",
      size_bytes: 409600,
    },
  },
  stale: false,
  stale_reasons: [],
  warnings: [],
  completed_at: "2026-09-02T12:00:45Z",
};

export const preparationFixtureReadyStale = {
  ...preparationFixtureReadyEligible,
  stale: true,
  stale_reasons: ["upstream_approved_hash_changed"],
};

export const preparationFixtureNeedsAttention = {
  status: "needs_attention",
  current_stage: "stage_3",
  latest_error: {
    message: "Failed to assemble route context from approved specifications.",
    code: "BUILD_PREPARATION_FAILED",
  },
  warnings: ["Missing mandatory section assets."],
  stale: false,
  stale_reasons: [],
};

export const preparationFixtureUnsupported = {
  status: "future_unsupported_status_omega",
};
