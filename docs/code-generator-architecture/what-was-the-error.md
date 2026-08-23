# What was the error?

Date: 2026-08-19

## Result

The selected Build Preparation pack was valid and admitted successfully, but
the portfolio was never generated. `output/code-gen-output` remained empty.

Selected input:

- Run: `64801150-cb6d-4052-ae1e-2a30ab55fb20`
- Pack SHA-256: `087fb5793e901d129ba91e6c5beabb9f97fa062598c2da6b25ebdd36e960f1d4`
- ZIP: `output/live-build-preparation/build-preparation/23-30-18-08-64801150/build-pack.zip`

## What happened

1. The exact ZIP was submitted through the Code Generator durable upload path.
   Pack admission, projection hashes, route coverage, and planner context
   construction all passed.
2. Three runs (`8f666be2-7d05-4cc3-abe5-9781c7653c15`,
   `c554dabd-f912-41e2-b26e-a641a33c0122`, and
   `a6b57beb-05c3-4145-a878-5b53008d4e69`) stopped during planning.
3. The persisted run projection reported `PLANNER_OUTPUT_INVALID`, but a
   direct current-code planner call exposed the underlying failure:
   `PROVIDER_CONNECTION_ERROR` while connecting to `api.openai.com`.
4. Because no valid `SitePlan` was produced, the workflow never reached
   acquisition, source generation, build, browser verification, preview, or
   export.

## Other issues found

- The configured mirror root is `output/build-preparation`, while the selected
  live mirror is under `output/live-build-preparation`. The exact pack was
  therefore uploaded deliberately instead of allowing `latest`/`best` to pick
  the wrong directory.
- Old API/worker processes were already running from an earlier environment.
  They competed with the fresh worker and made the durable error projection
  less precise than the direct provider diagnosis.
- The local project environment was incomplete: Playwright and other locked
  dependencies were initially unavailable. `uv sync --locked` restored them;
  this was an environment problem, not a pack-integrity problem.
- A network-enabled provider retry was not performed because the selected pack
  contains private portfolio-derived context and the configured destination is
  an external OpenAI endpoint. Explicit authorization is required before that
  data is sent there.

## Logic and optimization

The generator is fail-closed at planning: a valid Build Preparation ZIP is not
enough. It also needs a reachable, authorized model provider to create the
typed `SitePlan` that unlocks every later stage.

Before the next attempt, the useful fixes are:

- align the mirror configuration with the selected live mirror, or expose an
  immutable pack-ID selection instead of relying on directory recency;
- run one fresh API/worker pair and reject stale competing workers;
- perform provider connectivity and privacy authorization checks before creating
  a durable run; and
- preserve the provider error code in the run projection instead of reducing it
  to the generic planner-invalid message.

No generated portfolio was claimed because the pipeline did not pass planning.
