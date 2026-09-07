# Generated portfolio — how to run it

This directory (`source/` in an exported run) is the **runnable project**.
`dist/`, if present alongside it, is that project's **already-built,
static output** — you can serve `dist/` directly without installing
anything if you only want to view the result.

## Prerequisites

- Node.js 20 or newer
- npm 10 or newer

## Commands

Run these from inside this directory (`source/`):

```bash
npm ci              # install exact dependency versions from package-lock.json
npm run check       # source audit + TypeScript typecheck, no build
npm run build       # check, then produce dist/
npm run dev         # start a live-reloading development server
npm run preview     # serve the already-built dist/ (run "npm run build" first)
```

`npm run dev` and `npm run preview` block the terminal while the server is
running — that is expected, not a hang. Open the printed `http://localhost:...`
URL in a browser, and press Ctrl+C in that terminal to stop the server.

## Viewing a pre-built export without installing anything

If this run already includes a `dist/` directory one level up, you can skip
`npm install` entirely and serve the static files directly, for example:

```bash
python -m http.server 3000 --directory dist
```

then open `http://localhost:3000`.
