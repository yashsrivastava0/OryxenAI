# OryxenAI — Unified Agent Output Directory

This directory is the canonical destination for local and developer-facing
agent run outputs.

## Directory Structure

```text
output/
├── build-preparation/      # Build Preparation agent outputs
│   └── <timestamp>-<id>/
│       ├── content-and-narrative-brief.md   # Markdown brief with fenced JSON contract
│       ├── visual-and-build-brief.md        # Markdown brief with resource & design indices
│       └── generated-at.txt                 # Timestamp and run metadata
│
├── code-gen-output/        # Code Generator agent outputs
│   └── <timestamp>-<id>/
│       ├── dist/                            # Production build bundle
│       ├── source/                          # React + Vite source tree
│       ├── generation-report.md             # Generation run summary and audit log
│       └── portfolio.json                   # Structured portfolio metadata
│
└── README.md               # This documentation
```

## Policy & Retention

1. **Disposable by design**: Outputs in this directory are local courtesy/debug
   exports and developer mirrors. The system persists durable production state in
   PostgreSQL (`portfolio_sessions.current_state`) and configured artifact storage.
2. **Eligibility for Code Generator**: Code Generator discovers Build Preparation
   packs under `output/build-preparation/`. Only valid, schema-compliant Markdown
   brief pairs covering all admitted routes and closed navigation contracts are
   eligible.
3. **Maintenance**: Stale, corrupted, or ephemeral test runs can be pruned at any
   time while retaining benchmark and latest eligible packs.

## First-four agent exports

Live durable runs also write pure result receipts under:

```text
output/
├── discovery/<run-id>/result.json
├── content_architect/<run-id>/result.json
├── visual_design_director/<run-id>/result.json
└── build_preparation/<run-id>/result.json
```

Each run includes `run-metadata.json`; Build Preparation also includes its two
Markdown briefs. These files contain generated results and safe telemetry, not
raw prompts, resumes, API keys, or database state. The six-month result-cache
TTL and export root are configured in `[model_cache]` in `config/app.toml`.
