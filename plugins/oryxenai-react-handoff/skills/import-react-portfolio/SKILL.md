---
name: import-react-portfolio
description: Import, verify, build and preview a React portfolio from an OryxenAI share link through MCP before enhancing it.
---

Use this skill when the user provides an OryxenAI React handoff link and asks to continue their portfolio.

1. Read `get_react_project(share_link)` for metadata and expiry. Do not print or log the capability link. The server prepares React deterministically; do not ask a model to convert the original HTML.
2. Locate this plugin's root and install its pinned helper dependencies with `npm ci --prefix <plugin-root> --ignore-scripts --no-audit --no-fund` if absent.
3. Choose a new, unused directory in the user's workspace. Run `node <plugin-root>/scripts/import-project.mjs --endpoint <configured-mcp-url> --link <share-link> --destination <new-directory> --build`. Prefer supplying the link through the `ORYXENAI_SHARE_LINK` environment variable so it is absent from process arguments. Do not echo the variable or shell-trace the command. The helper transfers binary files directly to disk, verifies every chunk and file, and runs installation, type checking and a production build. Source chunks must stay outside the model's conversation.
4. If interrupted, resume only the same helper-owned directory with `--resume`. A changed or unrelated existing file must be reported, never overwritten. Expired/revoked links require a new handoff from the owner.
5. If the build passes, start `npm run dev` in the imported project using the host's supported background terminal. Open that local URL using the host preview capability when available. In Codex, use its browser panel for the local preview. If this host cannot render, say so explicitly. Do not claim a preview succeeded until it was opened and inspected.
6. Report the imported directory, type-check/build result, and preview capability before making the user's requested enhancements. Keep working in React and TypeScript. The project no longer needs OryxenAI after import.

For a view-only request in an MCP Apps host, call `show_react_portfolio`. Its React UI is optional; a tool response alone does not prove the host rendered it. Do not route source files through a download/ZIP endpoint.

The programmatic importer is tested against the actual MCP transport. Installed Codex plugin/preview support and other clients require separate client acceptance; do not claim those checks passed from a successful transfer alone.
