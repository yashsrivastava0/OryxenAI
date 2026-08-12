# Codex Handoff

**Handoff timestamp:** 2026-08-12 10:30:04 +05:30
**Repository:** OryxenAI
**Branches:** `main` and `working` are intended to point at the same handoff commit.
**Canonical instructions:** Read `AGENTS.md`, then `DECISIONS.md` and `CHANGES.md`.

## What is implemented

The portfolio pipeline is implemented through Build Preparation:

```text
Discovery -> Content Architect -> Visual Design Director -> Build Preparation
```

Every transition remains explicit. Build Preparation does not automatically
start Code Generator, and Code Generator remains intentionally deferred.

### Stage 0 / Step 0

- Retired the dead `src/oryxenai/build_preparation/` module and its stale
  routes, handlers, frontend assets, and tests.
- Removed only Build Preparation references from the old locations; unrelated
  Visual Design Director, configuration, and settings work was preserved.
- Confirmed there are no remaining legacy Python imports.

### Phase 1

- Added the provider-neutral Build Preparation agent under
  `src/oryxenai/agents/build_preparation/`.
- Added deterministic approval/scope compilation, public-route filtering,
  resource-need extraction, source hashes, state, service, API, registry, and
  durable worker wiring.
- Added the two-page developer harness:
  `/build-preparation-fixture` for input and
  `/build-preparation-fixture/progress` for progress/log inspection.
- Stage 0 makes zero model/provider calls.

### Phase 2

- Added bounded structured model stages for resource query composition,
  candidate selection, route build-context writing, and optional cross-route
  integration.
- Added live Pexels/Unsplash/registry/Lucide provider handling, explicit
  fallbacks, closed-set selection validation, and public-content filtering.
- Added deterministic build-context materialization with route briefs,
  resource manifests, licenses, target files, and provenance.

### Phase 3

- Added deterministic ZIP creation, manifest/checksum validation, immutable
  artifact storage, read-back verification, expiry metadata, and safe local
  debug mirrors.
- Added memory and S3-compatible storage implementations, including the
  configured temporary object-storage path.
- The full run is idempotent and does not expose provider credentials to the
  model or generated output.

## Harness follow-up included in this handoff

- The fixture API and UI now accept optional approved Content Architect JSON in
  addition to Visual Design Director JSON.
- The Content Architect input supports paste and file selection.
- Blank Content Architect input preserves the previous VDD-only behavior.
- Both structured-object and JSON-string forms have size, shape, malformed JSON,
  and ambiguous-input safeguards.
- Debug mirror folders now use the readable format
  `YYYY-MM-DD_HH-MM-SS-<8-char-run-id>/build-context/`.
- The complete run ID remains in `manifest.json`.
- A live approved-route smoke run produced a route brief, resource candidates,
  and a real locally materialized image.

## Docker and separate execution paths

The Docker Compose setup has two deliberately separate paths.

### Main workflow

```powershell
Copy-Item .env.example .env
# Fill only the required local secret values in .env.
docker compose up --build
```

This starts PostgreSQL, one-shot migrations, the FastAPI app/UI, and the
durable worker. The app is available at `http://localhost:8000` and PostgreSQL
is mapped to host port `5544`.

### Build Preparation validation

The validation service is behind the `build-validation` Compose profile and is
not started by the main workflow:

```powershell
# Deterministic offline validation with the checked-in VDD fixture.
docker compose --profile build-validation run --rm build-validation

# Optional live model/provider validation.
docker compose --profile build-validation run --rm build-validation --live-model --live-providers
```

It runs one detached Stage 0 through Phase 3 validation and exits. It does not
start the API, worker, migrations, or a session. The same path can be run
without Docker:

```powershell
uv run python -m oryxenai.agents.build_preparation.cli
uv run python -m oryxenai.agents.build_preparation.cli --live-model --live-providers
```

Useful CLI options are `--vdd-input`, `--content-architect-input`,
`--model-profile`, and `--output-dir`.

## Configuration and secrets

- Non-secret app/database/worker settings live in `config/app.toml` and the
  Docker overlay `config/app.docker.toml`.
- Model/provider selection is config-driven through `config/models.toml`.
- API keys, database passwords, and object-storage credentials remain in the
  ignored `.env`; never commit or print them.
- The Docker validation output directory is disposable container storage.
- Production Build Preparation artifacts use the configured temporary
  S3-compatible storage path; local Docker mirrors are disabled.

## Verification completed

The final repository state was verified with:

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
node --check src/oryxenai/web/static/build-preparation-fixture.js
git diff --check
```

The full test run passed with one expected opt-in live-test skip. Focused
Build Preparation tests, API tests, worker tests, static checks, and a live
model/provider/artifact-storage smoke run also passed. The live smoke verified
an approved route, non-empty resource needs, provider candidates, a per-route
brief, a real image file, and the readable mirror folder.

## Important deferred scope

- Code Generator remains a deterministic mock and is not wired to this stage.
- No automatic chaining, publishing automation, authentication, billing, or
  production portfolio deployment was added.
- The Build Preparation harness remains intentionally simple and two-page.

## Handoff rule

Before making architectural changes, read `DECISIONS.md`. Before trusting a
status claim, run the relevant tests and inspect the corresponding agent
directory. Keep the main workflow and the `build-validation` profile as
separate execution paths.
