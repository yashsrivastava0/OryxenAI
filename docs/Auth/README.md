# Authentication and ownership documentation

This directory records authentication design and implementation. For current
runtime behavior, read AGENTS.md and inspect src/oryxenai/auth/.

## Current boundary

- Supabase restores browser identity; the server verifies signed tokens.
- Verified users are admitted by configured account policy and complete
  username onboarding when required.
- Normal users own one portfolio session. The server enforces ownership on
  reads, mutations, and durable work.
- Administrators use separate audited routes for account and portfolio
  lifecycle operations.
- Workers reauthorize trusted owner/actor snapshots before applying changes.
- Historical run and output records remain stored for audit and are removed
  only through an explicit authorized cleanup operation.
- The active product workflow ends after approved Content Architect output.

## Current source of truth

- src/oryxenai/auth/ — identity, entitlement, ownership, worker fence, and
  administrator lifecycle implementation.
- src/oryxenai/api/dependencies.py — request authorization dependencies.
- src/oryxenai/api/projections.py — current session and run projections.
- migrations/ — schema history and forward migrations.
- AGENTS.md — canonical project context and operational rules.

The remaining files in this directory preserve prior design and implementation
history. Treat them as historical evidence when their claims differ from
current source.
