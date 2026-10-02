// Studio envelopes for the browser fixtures (what GET /code-generator returns).

type Envelope = Record<string, unknown>;

const failure = {
  code: "PAGE_COPY_MISMATCH",
  stage: "validate",
  summary: "The generated page failed 2 checks; first: The text for hero.intro differs from the approved copy.",
  cause: "The model changed, dropped, added or misplaced approved wording. Approved copy must appear exactly, in its own place.",
  where: [
    { kind: "field", ref: "hero.intro", detail: "The text for hero.intro differs from the approved copy." },
    { kind: "selector", ref: "section#technical-capabilities ul.capability-list li:nth-child(4)", detail: "Text is not part of the approved content." },
  ],
  expected: "Senior backend engineer at Northstar Systems",
  found: "Staff backend engineer at Northstar Systems",
  owner: "model_output",
  retryable: true,
  action: "Nothing was published and your last verified page is unchanged. Try again; if it repeats, copy the diagnostics for support.",
  issue_count: 2,
  reference: "cg-4f1a9c0b22",
  issues: [],
};

const versionOne = {
  id: "v1",
  seq: 1,
  version_number: 1,
  origin: "initial",
  status: "ready",
  instruction: "",
  restricted: false,
  completed_at: "2026-10-02T09:00:00+00:00",
  created_at: "2026-10-02T08:59:30+00:00",
  summary: { warning_count: 0, browser: "passed" },
};

const generator = (extra: Envelope = {}): Envelope => ({
  status: "ready",
  theme_id: "editorial-forest/v1",
  active_version_id: "v1",
  active_version_number: 1,
  in_flight: null,
  last_error: null,
  builds_started: 1,
  ...extra,
});

const wrap = (code_generator: Envelope, versions: Envelope[] = [], chat: Envelope[] = []): Envelope => ({
  session_id: "fixture-session",
  session_revision: 12,
  code_generator,
  versions,
  chat,
  jobs: [],
});

const readyChat = [
  { id: "c1", seq: 1, role: "assistant", kind: "build", body: "Building your portfolio from your approved content.", version_id: "v1", created_at: "2026-10-02T08:59:30+00:00" },
  { id: "c2", seq: 2, role: "assistant", kind: "build", body: "Your portfolio is ready (version 1).", version_id: "v1", created_at: "2026-10-02T09:00:00+00:00" },
];

export const studioFixtures = {
  byName(name: string): Envelope {
    switch (name) {
      case "studio-available":
        return wrap({ status: "not_started", theme_id: "", active_version_id: "", active_version_number: 0, in_flight: null, last_error: null, builds_started: 0 });
      case "studio-working":
        return wrap({
          status: "build_running",
          active_version_id: "",
          active_version_number: 0,
          in_flight: { run_id: "r1", job_id: "j1", version_id: "v1", origin: "initial", stage: "validating", elapsed_seconds: 18.2, started_at: "2026-10-02T08:59:30+00:00" },
          last_error: null,
          builds_started: 1,
        });
      case "studio-attention":
        return wrap({ status: "needs_attention", active_version_id: "", active_version_number: 0, in_flight: null, last_error: failure, builds_started: 1 });
      case "studio-failed-edit":
        return wrap(
          generator({ last_error: failure, active_version_number: 2, active_version_id: "v2" }),
          [
            { ...versionOne, id: "v2", seq: 2, version_number: 2, origin: "change", instruction: "Make my intro shorter" },
            versionOne,
          ],
          [
            ...readyChat,
            { id: "c3", seq: 3, role: "user", kind: "message", body: "Make my intro shorter", created_at: "2026-10-02T09:05:00+00:00" },
            { id: "c4", seq: 4, role: "assistant", kind: "message", body: "Shortened your intro.", version_id: "v2", created_at: "2026-10-02T09:05:20+00:00" },
            { id: "c5", seq: 5, role: "user", kind: "message", body: "Reword my headline", created_at: "2026-10-02T09:07:00+00:00" },
            { id: "c6", seq: 6, role: "system", kind: "build", body: "I couldn't apply that change. The generated page failed 2 checks; first: The text for hero.intro differs from the approved copy. Your last verified page is unchanged.", created_at: "2026-10-02T09:07:30+00:00" },
          ],
        );
      case "studio-workspace":
      case "studio-interactive":
      default:
        return wrap(generator(), [versionOne], readyChat);
    }
  },

  building(initial: unknown, message: string, next: number, stage: string): Envelope {
    const base = initial as Envelope;
    return {
      ...base,
      code_generator: {
        ...(base.code_generator as Envelope),
        status: "build_running",
        in_flight: { run_id: `r${next}`, job_id: `j${next}`, version_id: `v${next}`, origin: "change", instruction: message, stage, elapsed_seconds: 1, started_at: "2026-10-02T09:10:00+00:00" },
      },
      chat: [
        ...((base.chat as Envelope[]) ?? []),
        { id: `u${next}`, seq: 100 + next, role: "user", kind: "message", body: message, created_at: "2026-10-02T09:10:00+00:00" },
      ],
    };
  },

  afterChange(initial: unknown, message: string, next: number, _previous: unknown): Envelope {
    const base = initial as Envelope;
    const versions = (base.versions as Envelope[]) ?? [];
    return {
      ...base,
      code_generator: { ...(base.code_generator as Envelope), status: "ready", active_version_id: `v${next}`, active_version_number: next, in_flight: null, last_error: null },
      versions: [{ ...versionOne, id: `v${next}`, seq: next, version_number: next, origin: "change", instruction: message }, ...versions],
      chat: [
        ...((base.chat as Envelope[]) ?? []),
        { id: `u${next}`, seq: 100 + next, role: "user", kind: "message", body: message, created_at: "2026-10-02T09:10:00+00:00" },
        { id: `a${next}`, seq: 200 + next, role: "assistant", kind: "message", body: "Done. I updated that part of your page.", version_id: `v${next}`, created_at: "2026-10-02T09:10:20+00:00" },
      ],
    };
  },
};
