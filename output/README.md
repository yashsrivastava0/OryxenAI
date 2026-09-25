# OryxenAI Output Directory

This directory contains local exports from the active Discovery and Content
Architect workflows.

```text
output/
├── discovery/<run-id>/result.json
└── content_architect/<run-id>/result.json
```

Each run may also include `run-metadata.json`. These exports contain generated
results and safe run metadata; durable application state remains in the
configured database and artifact storage.
